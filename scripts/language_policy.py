from __future__ import annotations

import json
import re
from dataclasses import dataclass
from pathlib import Path
from typing import Annotated, ClassVar, Final

from pydantic import BaseModel, ConfigDict, Field, ValidationError

type JsonScalar = str | int | float | bool | None
type JsonValue = JsonScalar | list[JsonValue] | dict[str, JsonValue]


class LanguagePolicyRuleConfig(BaseModel):
    model_config: ClassVar[ConfigDict] = ConfigDict(extra="ignore", frozen=True)

    id: Annotated[str, Field(min_length=1)]
    patterns: Annotated[
        tuple[Annotated[str, Field(min_length=1)], ...], Field(min_length=1)
    ]


class LanguagePolicyConfig(BaseModel):
    model_config: ClassVar[ConfigDict] = ConfigDict(extra="ignore", frozen=True)

    disallowed: tuple[LanguagePolicyRuleConfig, ...] = Field(min_length=1)


class LanguagePolicyDocument(BaseModel):
    model_config: ClassVar[ConfigDict] = ConfigDict(extra="ignore", frozen=True)

    language_policy: LanguagePolicyConfig


class TopicPolicyRuleConfig(BaseModel):
    model_config: ClassVar[ConfigDict] = ConfigDict(extra="ignore", frozen=True)

    id: Annotated[str, Field(min_length=1)]
    patterns: Annotated[
        tuple[Annotated[str, Field(min_length=1)], ...], Field(min_length=1)
    ]


class BannedTopicsConfig(BaseModel):
    model_config: ClassVar[ConfigDict] = ConfigDict(extra="ignore", frozen=True)

    hard_banned: tuple[TopicPolicyRuleConfig, ...] = Field(min_length=1)
    review_required: tuple[TopicPolicyRuleConfig, ...] = Field(min_length=1)
    language_policy: LanguagePolicyConfig


@dataclass(frozen=True, slots=True)
class LanguagePolicyRule:
    code: str
    pattern: re.Pattern[str]


AUTHORED_PROSE_FIELDS: Final = frozenset(
    {
        "action",
        "audience",
        "background",
        "behavioral_contradiction",
        "camera",
        "engine_explanation",
        "escalation",
        "expression",
        "guidance",
        "hook_mode",
        "hook_promise",
        "human_truth",
        "issues",
        "payoff_reversal",
        "premise",
        "props",
        "scene",
        "text",
        "title",
        "tone",
        "topic",
        "twist",
        "why_relatable",
    }
)


POLICY_PATH = Path(__file__).resolve().parents[1] / "memory" / "banned-topics.json"
POLICY_CATEGORY_ORDER: Final = (
    "profanity",
    "obfuscation",
    "identity",
    "dehumanization",
)


def _language_policy_rules() -> tuple[LanguagePolicyRule, ...]:
    try:
        policy = LanguagePolicyDocument.model_validate_json(
            POLICY_PATH.read_text(encoding="utf-8")
        )
    except (OSError, UnicodeDecodeError, ValidationError) as error:
        raise RuntimeError(f"invalid language policy config at {POLICY_PATH}: {error}") from error

    rules_by_code: dict[str, LanguagePolicyRule] = {}
    for configured_rule in policy.language_policy.disallowed:
        code = configured_rule.id
        if code in rules_by_code:
            raise RuntimeError(f"invalid language policy rule in {POLICY_PATH}: {code!r}")
        try:
            pattern = re.compile("|".join(f"(?:{pattern})" for pattern in configured_rule.patterns))
        except re.error as error:
            raise RuntimeError(
                f"invalid language policy pattern for {code!r} in {POLICY_PATH}: {error}"
            ) from error
        rules_by_code[code] = LanguagePolicyRule(code, pattern)
    missing = tuple(
        code for code in POLICY_CATEGORY_ORDER if code not in rules_by_code
    )
    if missing:
        raise RuntimeError(
            f"invalid language policy config at {POLICY_PATH}: missing categories {missing}"
        )
    ordered = tuple(rules_by_code[code] for code in POLICY_CATEGORY_ORDER)
    extras = tuple(
        rule
        for code, rule in sorted(rules_by_code.items())
        if code not in POLICY_CATEGORY_ORDER
    )
    return ordered + extras


def _topic_policy_rules(
    configured_rules: tuple[TopicPolicyRuleConfig, ...], category: str
) -> tuple[LanguagePolicyRule, ...]:
    rules: list[LanguagePolicyRule] = []
    seen: set[str] = set()
    for configured_rule in configured_rules:
        if configured_rule.id in seen:
            raise RuntimeError(
                f"invalid {category} policy rule in {POLICY_PATH}: {configured_rule.id!r}"
            )
        seen.add(configured_rule.id)
        try:
            pattern = re.compile(
                "|".join(f"(?:{item})" for item in configured_rule.patterns)
            )
        except re.error as error:
            raise RuntimeError(
                f"invalid {category} policy pattern for {configured_rule.id!r} in {POLICY_PATH}: {error}"
            ) from error
        rules.append(LanguagePolicyRule(configured_rule.id, pattern))
    return tuple(rules)


def _banned_topics_config() -> BannedTopicsConfig:
    try:
        return BannedTopicsConfig.model_validate_json(POLICY_PATH.read_text(encoding="utf-8"))
    except (OSError, UnicodeDecodeError, ValidationError) as error:
        raise RuntimeError(f"invalid language policy config at {POLICY_PATH}: {error}") from error


def _authored_prose(value: JsonValue, authored: bool = False) -> tuple[str, ...]:
    if isinstance(value, str):
        return (value,) if authored else ()
    if isinstance(value, list):
        return tuple(item for child in value for item in _authored_prose(child, authored))
    if isinstance(value, dict):
        return tuple(
            item
            for key, child in value.items()
            if isinstance(key, str)
            for item in _authored_prose(child, authored or key in AUTHORED_PROSE_FIELDS)
        )
    return ()


def _prose_by_file(episode_dir: Path) -> tuple[tuple[Path, tuple[str, ...]], ...]:
    prose: list[tuple[Path, tuple[str, ...]]] = []
    for filename in ("brief.json", "script.json"):
        path = episode_dir / filename
        if not path.is_file():
            continue
        try:
            payload = json.loads(path.read_text(encoding="utf-8"))
        except (OSError, UnicodeDecodeError, json.JSONDecodeError):
            continue
        authored = _authored_prose(payload)
        if authored:
            prose.append((path, authored))
    caption = episode_dir / "caption.txt"
    if caption.is_file():
        prose.append((caption, (caption.read_text(encoding="utf-8"),)))
    return tuple(prose)


def _policy_issues(
    episode_dir: Path, rules: tuple[LanguagePolicyRule, ...], category: str
) -> tuple[str, ...]:
    issues: list[str] = []
    for path, prose in _prose_by_file(episode_dir):
        text = "\n".join(prose)
        for rule in rules:
            if rule.pattern.search(text):
                issues.append(f"{category} {rule.code} in {path}")
    return tuple(issues)


def language_policy_issues(episode_dir: Path) -> tuple[str, ...]:
    return _policy_issues(episode_dir, _language_policy_rules(), "language_policy")


def hard_banned_issues(episode_dir: Path) -> tuple[str, ...]:
    policy = _banned_topics_config()
    return _policy_issues(
        episode_dir,
        _topic_policy_rules(policy.hard_banned, "hard_banned"),
        "hard_banned",
    )


def review_required_findings(episode_dir: Path) -> tuple[str, ...]:
    policy = _banned_topics_config()
    return _policy_issues(
        episode_dir,
        _topic_policy_rules(policy.review_required, "review_required"),
        "review_required",
    )
