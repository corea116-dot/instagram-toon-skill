"""Validate independent informational review records and their input bindings.

The reviewer supplies semantic judgments after a blind read. This module checks
the record, quoted evidence, coverage, and freshness; it does not determine the
truth of a financial or policy claim by itself.
"""

from __future__ import annotations

import hashlib
import json
from pathlib import Path
from typing import Annotated, Literal, Self

from episode_models import BriefModel, EpisodeScriptModel, NonBlankString, StrictModel
from pydantic import (
    AwareDatetime,
    Field,
    StringConstraints,
    ValidationError,
    model_validator,
)

Sha256 = Annotated[str, StringConstraints(pattern=r"^[0-9a-f]{64}$")]


class BlindReadModel(StrictModel):
    completed_at: AwareDatetime
    topic_understood: NonBlankString
    learned: NonBlankString
    next_action: NonBlankString


class BlindReadV11Model(BlindReadModel):
    reader_question_recalled: NonBlankString
    action_steps: Annotated[
        tuple[NonBlankString, ...], Field(min_length=1, max_length=3)
    ]
    repeated_panels: tuple[NonBlankString, ...] = ()
    awkward_phrases: tuple[NonBlankString, ...] = ()
    where_to_check_next: NonBlankString


class ReviewCheckModel(StrictModel):
    passed: bool
    evidence: NonBlankString


class ContentChecksModel(StrictModel):
    answers_reader_question: ReviewCheckModel
    topic_specificity: ReviewCheckModel
    claims_sources_conditions: ReviewCheckModel
    benefits_conditions_risks: ReviewCheckModel
    standalone_comprehension: ReviewCheckModel
    dialogue_numbers_continuity: ReviewCheckModel


class ContentChecksV11Model(ContentChecksModel):
    promise_payoff_alignment: ReviewCheckModel
    distinct_panel_value: ReviewCheckModel
    ending_actionability: ReviewCheckModel
    scope_consistency: ReviewCheckModel
    korean_naturalness: ReviewCheckModel
    layout_density: ReviewCheckModel


class ClaimCoverageModel(StrictModel):
    fact_id: NonBlankString
    panel: Annotated[int, Field(ge=1)]
    script_quote: NonBlankString
    source_urls: Annotated[tuple[NonBlankString, ...], Field(min_length=1)]
    assessment: NonBlankString


class ContentReviewModel(StrictModel):
    schema_version: Literal["1.0", "1.1"]
    episode_id: NonBlankString
    writer_id: NonBlankString
    reviewer_id: NonBlankString
    brief_sha256: Sha256 | None = None
    script_sha256: Sha256 | None = None
    content_sha256: Sha256 | None = None
    layout_sha256: Sha256 | None = None
    stages: tuple[Literal["blind_read"], Literal["card_source_checks"]]
    blind_read: BlindReadModel | BlindReadV11Model
    checked_at: AwareDatetime
    checks: ContentChecksModel | ContentChecksV11Model
    claim_coverage: Annotated[tuple[ClaimCoverageModel, ...], Field(min_length=1)]
    review_round: Annotated[int, Field(ge=1, le=3)] = 1
    additional_review_reason: NonBlankString | None = None
    outcome: Literal["pass", "fail"]

    @model_validator(mode="after")
    def review_contract(self) -> Self:
        if self.writer_id == self.reviewer_id:
            raise ValueError(
                "content review requires a reviewer different from the writer"
            )
        if self.checked_at <= self.blind_read.completed_at:
            raise ValueError("card/source checks must follow the blind read")
        if self.review_round > 1 and self.additional_review_reason is None:
            raise ValueError("additional reviews require a reason")
        if self.schema_version == "1.0":
            if self.brief_sha256 is None or self.script_sha256 is None:
                raise ValueError(
                    "review schema 1.0 requires brief_sha256 and script_sha256"
                )
            if self.content_sha256 is not None or self.layout_sha256 is not None:
                raise ValueError(
                    "review schema 1.0 must not use split content/layout hashes"
                )
            if isinstance(self.blind_read, BlindReadV11Model) or isinstance(
                self.checks, ContentChecksV11Model
            ):
                raise ValueError(
                    "review schema 1.0 requires the legacy blind read and checks"
                )
        else:
            if self.content_sha256 is None or self.layout_sha256 is None:
                raise ValueError(
                    "review schema 1.1 requires content_sha256 and layout_sha256"
                )
            if self.brief_sha256 is not None or self.script_sha256 is not None:
                raise ValueError("review schema 1.1 must use split hashes")
            if not isinstance(self.blind_read, BlindReadV11Model) or not isinstance(
                self.checks, ContentChecksV11Model
            ):
                raise ValueError(
                    "review schema 1.1 requires expanded blind-read checks"
                )
            if (
                self.checks.distinct_panel_value.passed
                and self.blind_read.repeated_panels
            ):
                raise ValueError("a distinct-panel pass cannot retain repeated panels")
            if (
                self.checks.korean_naturalness.passed
                and self.blind_read.awkward_phrases
            ):
                raise ValueError(
                    "a Korean-naturalness pass cannot retain awkward phrases"
                )
        all_pass = all(check["passed"] for check in self.checks.model_dump().values())
        if (self.outcome == "pass") != all_pass:
            raise ValueError("review outcome must match every hard check")
        return self


def file_sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def _canonical_sha256(payload: object) -> str:
    encoded = json.dumps(
        payload,
        ensure_ascii=False,
        sort_keys=True,
        separators=(",", ":"),
    ).encode("utf-8")
    return hashlib.sha256(encoded).hexdigest()


def _semantic_payload(
    brief: BriefModel, script: EpisodeScriptModel
) -> dict[str, object]:
    brief_payload = brief.model_dump(mode="json", exclude={"output_layout", "status"})
    panel_payloads: list[dict[str, object]] = []
    for raw_panel in script.model_dump(mode="json")["panels"]:
        panel = dict(raw_panel)
        panel.pop("text_budget", None)
        card = panel.pop("information_card", None)
        if card is not None:
            panel["information_card"] = {
                "format": card["format"], "design_reason": card["design_reason"],
                "texts": [{"id": text["id"], "text": text["text"]} for text in card["texts"]],
                "presenter": {key: card["presenter"][key] for key in ("character_id", "pose", "explanation_bubble")},
            }
        panel["dialogue"] = [
            {"speaker": dialogue["speaker"], "text": dialogue["text"]}
            for dialogue in panel["dialogue"]
        ]
        panel_payloads.append(panel)
    return {
        "brief": brief_payload,
        "script": {
            "episode_id": script.episode_id,
            "title": script.title,
            "panels": panel_payloads,
        },
    }


def semantic_content_sha256(brief_path: Path, script_path: Path) -> str:
    brief = BriefModel.model_validate_json(brief_path.read_text(encoding="utf-8"))
    script = EpisodeScriptModel.model_validate_json(
        script_path.read_text(encoding="utf-8")
    )
    return _canonical_sha256(_semantic_payload(brief, script))


def layout_sha256(script_path: Path) -> str:
    script = EpisodeScriptModel.model_validate_json(
        script_path.read_text(encoding="utf-8")
    )
    payload = {
        "episode_id": script.episode_id,
        "output_layout": script.output_layout,
        "panels": [
            {
                "panel": panel.panel,
                "text_budget": panel.text_budget,
                "dialogue": [
                    dialogue.model_dump(mode="json", exclude={"tail_anchor"} if dialogue.tail_anchor is None else set()) for dialogue in panel.dialogue
                ],
                **({"information_card": panel.information_card.model_dump(mode="json")} if panel.information_card else {}),
            }
            for panel in script.panels
        ],
    }
    if script.rendering_policy == "frame_native_v1":
        payload.update(rendering_policy=script.rendering_policy, panel_sizes=script.panel_sizes())
    return _canonical_sha256(payload)


def content_review_issues(episode_dir: Path) -> tuple[str, ...]:
    """Legacy episodes need no new review. Malformed information records fail closed."""
    brief_path = episode_dir / "brief.json"
    if not brief_path.is_file():
        return ()
    try:
        payload = json.loads(brief_path.read_text(encoding="utf-8"))
        if not isinstance(payload, dict):
            return ("content review: brief.json must contain an object",)
        if payload.get("content_type") != "informational":
            return ()
        brief = BriefModel.model_validate(payload)
        script_path = episode_dir / "script.json"
        script = EpisodeScriptModel.model_validate_json(
            script_path.read_text(encoding="utf-8")
        )
        review_path = episode_dir / "content-review.json"
        review = ContentReviewModel.model_validate_json(
            review_path.read_text(encoding="utf-8")
        )
    except (OSError, UnicodeError, ValueError, ValidationError) as error:
        return (f"content review: {error}",)
    issues: list[str] = []
    if review.outcome != "pass":
        issues.append("content review has not passed every hard check")
    if review.schema_version == "1.0":
        if review.brief_sha256 != file_sha256(
            brief_path
        ) or review.script_sha256 != file_sha256(script_path):
            issues.append("content review is stale: brief/script SHA-256 mismatch")
    elif review.content_sha256 != semantic_content_sha256(brief_path, script_path):
        issues.append("content review is stale: semantic content SHA-256 mismatch")
    if brief.schema_version == "1.3":
        if script.schema_version != "1.2":
            issues.append("brief schema 1.3 requires informational script schema 1.2")
        if review.schema_version != "1.1":
            issues.append("brief schema 1.3 requires content review schema 1.1")
        if isinstance(review.blind_read, BlindReadV11Model):
            assert brief.question_answer is not None
            if len(review.blind_read.action_steps) != len(
                brief.question_answer.reader_actions
            ):
                issues.append(
                    "blind reader must restate the same number of concrete reader actions"
                )
    if review.episode_id != brief.episode_id or brief.episode_id != script.episode_id:
        issues.append("content review, brief and script episode IDs must match")
    if brief.title != script.title or brief.output_layout != script.output_layout:
        issues.append("informational brief and script title/output_layout must match")
    if (
        brief.duplicate_check.result != "pass"
        or brief.sensitivity_check.result != "pass"
    ):
        issues.append("informational duplicate and sensitivity checks must pass")
    assert brief.question_answer is not None
    for panel in script.panels:
        if panel.information_card and panel.information_card.presenter.character_id not in brief.characters:
            issues.append(f"panel {panel.panel} information card presenter is absent from brief characters")
    facts = {fact.id: fact for fact in brief.question_answer.required_facts}
    covered = {coverage.fact_id for coverage in review.claim_coverage}
    if covered != set(facts):
        issues.append(
            "content review claim coverage must cover every required fact and no unknown fact"
        )
    for coverage in review.claim_coverage:
        if coverage.panel > len(script.panels):
            issues.append(f"content review references missing panel {coverage.panel}")
            continue
        panel = script.panels[coverage.panel - 1]
        visible_text = "\n".join(line.text for line in panel.dialogue)
        if panel.information_card:
            visible_text += "\n" + "\n".join(text.text for text in panel.information_card.texts)
        if coverage.script_quote not in visible_text:
            issues.append(
                f"content review quote is absent from panel {coverage.panel} dialogue/card text"
            )
        fact = facts.get(coverage.fact_id)
        if fact is not None:
            known_urls = {str(source.url) for source in fact.sources}
            if not set(coverage.source_urls).issubset(known_urls):
                issues.append(
                    f"content review has unknown source for fact {coverage.fact_id}"
                )
    return tuple(issues)


def require_content_review(episode_dir: Path) -> None:
    issues = content_review_issues(episode_dir)
    if issues:
        raise ValueError("; ".join(issues))
