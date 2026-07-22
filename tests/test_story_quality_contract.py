#!/usr/bin/env -S uv run --script
# /// script
# requires-python = ">=3.12"
# dependencies = [
#     "pydantic>=2.12",
#     "pytest>=9.0",
#     "typer>=0.20",
# ]
# ///

from __future__ import annotations

import json
from pathlib import Path
import subprocess
import sys
from typing import cast

import pytest
from pydantic import ValidationError


SKILL_ROOT = Path(__file__).resolve().parents[1]
SCRIPTS = SKILL_ROOT / "scripts"
sys.path.insert(0, str(SCRIPTS))

def _candidate(identifier: str, total: int, eligible: bool, engine: str) -> dict[str, object]:
    return {
        "id": identifier,
        "topic": f"소재 {identifier}",
        "observation": "퇴근 직후 침대에 앉아 휴대폰을 켠다",
        "story_seed": "침대가 회의실처럼 퇴근을 연장한다",
        "source_ids": ["source-1", "source-2"],
        "source_signal": "공개 출처가 반복적으로 지지한 퇴근 뒤 행동",
        "source_relevance": "두 출처 모두 퇴근 후 휴대폰 사용이라는 관찰을 뒷받침한다",
        "human_observation": "쉬려고 누운 사람이 휴대폰부터 켠다",
        "behavioral_contradiction": "쉬려고 누웠지만 더 오래 일상을 미룬다",
        "humor_engine_id": engine,
        "engine_explanation": "익숙한 물건이 권한을 가진 것처럼 행동해 기대를 뒤집는다",
        "hook_seed": "침대가 왜 출근 체크를 하지?",
        "payoff_seed": "침대가 퇴근을 승인한다",
        "beat_signature": f"{engine}|resting-becomes-shift",
        "eligibility": eligible,
        "gate_results": {
            "source_relevance": eligible,
            "human_observation": eligible,
            "behavioral_contradiction": eligible,
            "humor_engine": eligible,
            "hook_seed": eligible,
            "payoff_seed": eligible,
            "safety": eligible,
            "duplicate": eligible,
        },
        "scores": {
            "relatability": 25,
            "humor": 25,
            "opening_hook": 16,
            "novelty": 9,
            "production_fit": total - 75,
            "total": total,
        },
    }


def _research_payload() -> dict[str, object]:
    engines = (
        "semantic_authority_reversal",
        "personified_cognition_action_contradiction",
        "self_rationalization_loop",
        "magnitude_mismatch",
        "semantic_authority_reversal",
    )
    candidates = [
        _candidate("high-ineligible", 85, False, engines[0]),
        *[
            _candidate(f"eligible-{number}", 84 - number, True, engines[number])
            for number in range(1, 5)
        ],
    ]
    return {
        "schema_version": "1.1",
        "source_mode": "public_web",
        "search_window_days": 30,
        "sources": [
            {
                "id": "source-1",
                "kind": "public_page",
                "url": "https://example.com/one",
                "title": "신호 하나",
                "observation": "퇴근 뒤 휴대폰을 보는 습관",
                "accessed_at": "2026-07-20T00:00:00+00:00",
            },
            {
                "id": "source-2",
                "kind": "public_page",
                "url": "https://example.com/two",
                "title": "신호 둘",
                "observation": "휴식 전 미루기 행동",
                "accessed_at": "2026-07-20T00:00:00+00:00",
            },
        ],
        "candidates": candidates,
        "selected_candidate_id": "eligible-1",
        "selected_topic": "소재 eligible-1",
        "selection_reason": "가장 높은 적격 후보",
        "fallback_reason": None,
    }


def _direction(identifier: str, engine: str = "semantic_authority_reversal") -> dict[str, object]:
    return {
        "id": identifier,
        "premise": "침대가 퇴근을 승인하는 이야기",
        "human_truth": "쉬려다 휴대폰으로 시간을 더 쓴다",
        "behavioral_contradiction": "쉬려고 누웠지만 더 오래 일상을 미룬다",
        "humor_engine_id": engine,
        "engine_explanation": "침대가 상사처럼 퇴근을 승인한다",
        "hook_promise": "침대가 왜 출근 체크를 하지?",
        "development_changes": ["눕는다", "휴대폰을 켠다", "체크인을 받는다", "승인을 기다린다"],
        "payoff_reversal": "침대가 퇴근을 승인한다",
        "beat_signature": "resting-becomes-shift",
        "why_relatable": "퇴근 후 휴대폰을 보는 습관",
    }


def _brief_payload(
    *, schema_version: str, topic_origin: str, topic: str = "소재 eligible-1"
) -> dict[str, object]:
    legacy_directions = [
        {"id": key, "premise": "전제", "escalation": "상승", "twist": "반전", "why_relatable": "공감"}
        for key in ("A", "B", "C")
    ]
    payload: dict[str, object] = {
        "schema_version": schema_version,
        "episode_id": "EP-001",
        "title": "제목",
        "topic": topic,
        "topic_origin": topic_origin,
        "audience": "직장인",
        "tone": "공감 유머",
        "characters": ["bgoon"],
        "directions": legacy_directions,
        "selected_direction": "A",
        "duplicate_check": {"matched_episode_ids": [], "result": "pass"},
        "sensitivity_check": {"issues": [], "result": "pass"},
    }
    if schema_version == "1.1":
        payload.update(
            {
                "directions": [
                    _direction("A"),
                    _direction("B", "magnitude_mismatch"),
                    _direction("C", "self_rationalization_loop"),
                ],
                "selected_humor_engine_id": "semantic_authority_reversal",
                "selected_beat_signature": "resting-becomes-shift",
                "hook_mode": "specific_contradiction",
            }
        )
    return payload


def _legacy_research_payload() -> dict[str, object]:
    payload = _research_payload()
    candidates = payload["candidates"]
    assert isinstance(candidates, list)
    for candidate in candidates:
        assert isinstance(candidate, dict)
        for field in (
            "source_signal",
            "source_relevance",
            "human_observation",
            "behavioral_contradiction",
            "humor_engine_id",
            "engine_explanation",
            "hook_seed",
            "payoff_seed",
            "beat_signature",
            "eligibility",
            "gate_results",
        ):
            candidate.pop(field)
    payload["schema_version"] = "1.0"
    payload["selected_candidate_id"] = "high-ineligible"
    payload["selected_topic"] = "소재 high-ineligible"
    return payload


def test_topic_research_selects_highest_eligible_candidate_when_higher_score_is_ineligible() -> None:
    from topic_research_models import TopicResearchModel

    payload = _research_payload()

    result = TopicResearchModel.model_validate(payload)

    assert result.selected_candidate_id == "eligible-1"


def test_topic_research_rejects_selecting_ineligible_high_score_candidate() -> None:
    from topic_research_models import TopicResearchModel

    payload = _research_payload()
    payload["selected_candidate_id"] = "high-ineligible"
    payload["selected_topic"] = "소재 high-ineligible"

    with pytest.raises(ValidationError, match="eligible"):
        _ = TopicResearchModel.model_validate(payload)


def test_brief_v11_requires_complete_direction_contract_while_v10_remains_readable() -> None:
    from episode_models import BriefModel

    legacy = {
        "schema_version": "1.0",
        "episode_id": "EP-001",
        "title": "legacy",
        "topic": "주제",
        "audience": "직장인",
        "tone": "공감 유머",
        "characters": ["bgoon"],
        "directions": [
            {"id": key, "premise": "전제", "escalation": "상승", "twist": "반전", "why_relatable": "공감"}
            for key in ("A", "B", "C")
        ],
        "selected_direction": "A",
        "duplicate_check": {"matched_episode_ids": [], "result": "pass"},
        "sensitivity_check": {"issues": [], "result": "pass"},
    }
    modern = cast(dict[str, object], legacy | {
        "schema_version": "1.1",
        "directions": [
            _direction("A"),
            _direction("B", "magnitude_mismatch"),
            _direction("C", "self_rationalization_loop"),
        ],
        "selected_humor_engine_id": "semantic_authority_reversal",
        "selected_beat_signature": "resting-becomes-shift",
        "hook_mode": "specific_contradiction",
    })

    assert BriefModel.model_validate(legacy).schema_version == "1.0"
    assert BriefModel.model_validate(modern).schema_version == "1.1"

    modern_directions = cast(list[dict[str, object]], modern["directions"])
    modern["directions"] = modern_directions[:2]
    with pytest.raises(ValidationError):
        _ = BriefModel.model_validate(modern)


def test_v11_rejects_homogeneous_direction_engines_and_unknown_engine() -> None:
    from episode_models import BriefModel

    modern = {
        "schema_version": "1.1",
        "episode_id": "EP-001",
        "title": "제목",
        "topic": "주제",
        "audience": "직장인",
        "tone": "공감 유머",
        "characters": ["bgoon"],
        "directions": [_direction(key) for key in ("A", "B", "C")],
        "selected_direction": "A",
        "duplicate_check": {"matched_episode_ids": [], "result": "pass"},
        "sensitivity_check": {"issues": [], "result": "pass"},
        "selected_humor_engine_id": "semantic_authority_reversal",
        "selected_beat_signature": "resting-becomes-shift",
        "hook_mode": "specific_contradiction",
    }
    with pytest.raises(ValidationError, match="two distinct primary humor engines"):
        _ = BriefModel.model_validate(modern)
    modern["directions"] = [
        _direction("A"),
        _direction("B", "other"),
        _direction("C", "other"),
    ]
    with pytest.raises(ValidationError, match="two distinct primary humor engines"):
        _ = BriefModel.model_validate(modern)
    modern["directions"] = [
        _direction("A"),
        _direction("B", "magnitude_mismatch"),
        _direction("C", "other"),
    ]
    directions = cast(list[dict[str, object]], modern["directions"])
    directions[2]["engine_explanation"] = "   "
    with pytest.raises(ValidationError, match="at least 1 character"):
        _ = BriefModel.model_validate(modern)
    directions[2]["engine_explanation"] = "별도 관찰을 뒤집는 방식이다"
    assert BriefModel.model_validate(modern).schema_version == "1.1"
    directions[2]["humor_engine_id"] = "invented_engine"
    with pytest.raises(ValidationError):
        _ = BriefModel.model_validate(modern)


@pytest.mark.parametrize(
    "mutate",
    [
        lambda candidate: candidate.pop("source_signal"),
        lambda candidate: candidate.pop("source_relevance"),
        lambda candidate: candidate.pop("human_observation"),
        lambda candidate: candidate.pop("behavioral_contradiction"),
        lambda candidate: candidate.pop("humor_engine_id"),
        lambda candidate: candidate.pop("engine_explanation"),
        lambda candidate: candidate.pop("hook_seed"),
        lambda candidate: candidate.pop("payoff_seed"),
        lambda candidate: candidate.pop("beat_signature"),
        lambda candidate: candidate["gate_results"].pop("duplicate"),
        lambda candidate: candidate["gate_results"].__setitem__("wrong_gate", True),
        lambda candidate: candidate.__setitem__("eligibility", True),
    ],
)
def test_v11_rejects_incomplete_or_inconsistent_editorial_evidence(mutate: object) -> None:
    from topic_research_models import TopicResearchModel

    payload = _research_payload()
    candidates = cast(list[dict[str, object]], payload["candidates"])
    candidate = candidates[0]
    assert callable(mutate)
    mutate(candidate)
    with pytest.raises(ValidationError):
        _ = TopicResearchModel.model_validate(payload)


def test_v11_rejects_coerced_editorial_gate_values() -> None:
    from topic_research_models import TopicResearchModel

    payload = _research_payload()
    candidates = cast(list[dict[str, object]], payload["candidates"])
    gate_results = cast(dict[str, object], candidates[0]["gate_results"])
    gate_results["safety"] = "false"

    with pytest.raises(ValidationError):
        _ = TopicResearchModel.model_validate(payload)


def test_v11_rejects_homogeneous_candidate_engines() -> None:
    from topic_research_models import TopicResearchModel

    payload = _research_payload()
    candidates = payload["candidates"]
    assert isinstance(candidates, list)
    for candidate in candidates[1:]:
        assert isinstance(candidate, dict)
        candidate["humor_engine_id"] = "other"
    with pytest.raises(ValidationError, match="three distinct primary humor engines"):
        _ = TopicResearchModel.model_validate(payload)


def test_v11_rejects_candidate_engines_with_only_two_distinct_primary_engines() -> None:
    from topic_research_models import TopicResearchModel

    payload = _research_payload()
    candidates = cast(list[dict[str, object]], payload["candidates"])
    for candidate, engine in zip(
        candidates,
        (
            "semantic_authority_reversal",
            "semantic_authority_reversal",
            "magnitude_mismatch",
            "other",
            "other",
        ),
        strict=True,
    ):
        candidate["humor_engine_id"] = engine
    with pytest.raises(ValidationError, match="three distinct primary humor engines"):
        _ = TopicResearchModel.model_validate(payload)


def test_v11_rejects_blank_other_candidate_engine_explanation() -> None:
    from topic_research_models import TopicResearchModel

    payload = _research_payload()
    candidates = cast(list[dict[str, object]], payload["candidates"])
    candidate = candidates[-1]
    candidate["humor_engine_id"] = "other"
    candidate["engine_explanation"] = "\t"
    with pytest.raises(ValidationError, match="at least 1 character"):
        _ = TopicResearchModel.model_validate(payload)


def test_topic_research_v10_remains_readable() -> None:
    from topic_research_models import TopicResearchModel

    assert TopicResearchModel.model_validate(_legacy_research_payload()).schema_version == "1.0"


def test_topic_research_validation_orders_brief_before_research_parsing(tmp_path: Path) -> None:
    from topic_research_validation import topic_research_issues

    episode = tmp_path / "episode"
    episode.mkdir()
    (episode / "topic-research.json").write_text("{}", encoding="utf-8")
    (episode / "brief.json").write_text(
        json.dumps(_brief_payload(schema_version="1.0", topic_origin="user"), ensure_ascii=False),
        encoding="utf-8",
    )
    assert topic_research_issues(episode) == ()

    (episode / "brief.json").write_text(
        json.dumps(_brief_payload(schema_version="1.0", topic_origin="editorial_scout"), ensure_ascii=False),
        encoding="utf-8",
    )
    issues = topic_research_issues(episode)
    assert len(issues) == 1
    assert "brief schema 1.1" in issues[0]
    assert "invalid structured file" not in issues[0]


def test_editorial_topic_research_requires_v11_and_matching_brief_topic(tmp_path: Path) -> None:
    from topic_research_validation import topic_research_issues

    episode = tmp_path / "episode"
    episode.mkdir()
    (episode / "brief.json").write_text(
        json.dumps(
            _brief_payload(
                schema_version="1.1",
                topic_origin="editorial_scout",
                topic="소재 high-ineligible",
            ),
            ensure_ascii=False,
        ),
        encoding="utf-8",
    )
    (episode / "topic-research.json").write_text(
        json.dumps(_legacy_research_payload(), ensure_ascii=False), encoding="utf-8"
    )
    issues = topic_research_issues(episode)
    assert len(issues) == 1
    assert "topic research schema 1.1" in issues[0]

    (episode / "topic-research.json").write_text(
        json.dumps(_research_payload(), ensure_ascii=False), encoding="utf-8"
    )
    (episode / "brief.json").write_text(
        json.dumps(
            _brief_payload(
                schema_version="1.1", topic_origin="editorial_scout", topic="다른 소재"
            ),
            ensure_ascii=False,
        ),
        encoding="utf-8",
    )
    issues = topic_research_issues(episode)
    assert len(issues) == 1
    assert "selected topic does not match brief topic" in issues[0]


@pytest.mark.parametrize(
    ("text", "expected_code"),
    [
        ("아 씨발", "profanity"),
        ("아 ㅆㅂ", "obfuscation"),
        ("그 집단은 벌레야", "dehumanization"),
        ("짱깨라고 부른다", "identity"),
    ],
)
def test_language_policy_rejects_profanity_and_obfuscation(tmp_path: Path, text: str, expected_code: str) -> None:
    episode = tmp_path / "episode"
    episode.mkdir()
    (episode / "script.json").write_text(
        json.dumps({"schema_version": "1.0", "episode_id": "EP-001", "title": "제목", "panels": []}, ensure_ascii=False),
        encoding="utf-8",
    )
    (episode / "caption.txt").write_text(text, encoding="utf-8")

    from language_policy import language_policy_issues

    assert expected_code in " ".join(language_policy_issues(episode))


@pytest.mark.parametrize(
    ("text", "expected_code"),
    (
        ("짱깨는 다 벌레야", "identity"),
        ("외국인들은 해충이다", "dehumanization"),
    ),
)
def test_language_policy_rejects_identity_and_dehumanizing_attacks(
    tmp_path: Path, text: str, expected_code: str
) -> None:
    episode = tmp_path / "episode"
    episode.mkdir()
    (episode / "caption.txt").write_text(text, encoding="utf-8")

    from language_policy import language_policy_issues

    assert expected_code in " ".join(language_policy_issues(episode))


def test_validation_allows_rough_non_profane_korean(tmp_path: Path) -> None:
    episode = tmp_path / "episode"
    episode.mkdir()
    (episode / "caption.txt").write_text("망했다. 이게 맞아? 큰일 났네.", encoding="utf-8")

    from language_policy import language_policy_issues

    assert language_policy_issues(episode) == ()


def test_hard_banned_policy_ignores_json_metadata_values(tmp_path: Path) -> None:
    episode = tmp_path / "episode"
    episode.mkdir()
    (episode / "brief.json").write_text(
        json.dumps(
            {"episode_id": "자해를 권한다", "topic": "퇴근 후 휴식"},
            ensure_ascii=False,
        ),
        encoding="utf-8",
    )

    from language_policy import hard_banned_issues

    assert hard_banned_issues(episode) == ()


def test_language_policy_loads_required_categories_in_deterministic_order(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    import language_policy

    policy_path = tmp_path / "policy.json"
    policy_path.write_text(
        json.dumps(
            {
                "language_policy": {
                    "disallowed": [
                        {"id": "identity", "patterns": ["i"]},
                        {"id": "profanity", "patterns": ["p"]},
                        {"id": "dehumanization", "patterns": ["d"]},
                        {"id": "obfuscation", "patterns": ["o"]},
                    ]
                }
            }
        ),
        encoding="utf-8",
    )
    monkeypatch.setattr(language_policy, "POLICY_PATH", policy_path)
    episode = tmp_path / "episode"
    episode.mkdir()
    (episode / "caption.txt").write_text("ipdo", encoding="utf-8")

    assert language_policy.language_policy_issues(episode) == (
        f"language_policy profanity in {episode / 'caption.txt'}",
        f"language_policy obfuscation in {episode / 'caption.txt'}",
        f"language_policy identity in {episode / 'caption.txt'}",
        f"language_policy dehumanization in {episode / 'caption.txt'}",
    )


def test_history_update_persists_selected_story_quality_metadata(tmp_path: Path) -> None:
    episode = tmp_path / "episode"
    episode.mkdir()
    (episode / "brief.json").write_text(
        json.dumps(
            {
                "schema_version": "1.1",
                "episode_id": "EP-009",
                "title": "퇴근 승인",
                "topic": "퇴근 후 침대",
                "characters": ["bgoon"],
                "selected_humor_engine_id": "semantic_authority_reversal",
                "selected_beat_signature": "resting-becomes-shift",
                "hook_mode": "specific_contradiction",
            },
            ensure_ascii=False,
        ),
        encoding="utf-8",
    )
    (episode / "script.json").write_text(
        json.dumps(
            {
                "schema_version": "1.0",
                "episode_id": "EP-009",
                "title": "퇴근 승인",
                "panels": [
                    {
                        "panel": number,
                        "beat": beat,
                        "scene": "장면",
                        "expression": "표정",
                        "action": "행동",
                        "props": [],
                        "background": "배경",
                        "camera": "구도",
                        "dialogue": [],
                    }
                    for number, beat in enumerate(
                        ("setup", "escalation", "tension", "twist"), start=1
                    )
                ],
            },
            ensure_ascii=False,
        ),
        encoding="utf-8",
    )
    history = tmp_path / "episode-history.json"
    history.write_text('{"schema_version":"1.0","episodes":[]}\n', encoding="utf-8")

    result = subprocess.run(
        [
            sys.executable,
            str(SCRIPTS / "update_history.py"),
            "--episode-dir",
            str(episode),
            "--history",
            str(history),
            "--status",
            "draft",
        ],
        check=False,
        capture_output=True,
        text=True,
    )

    assert result.returncode == 0, result.stderr
    payload = json.loads(history.read_text(encoding="utf-8"))
    assert payload["schema_version"] == "1.1"
    assert payload["episodes"][0]["humor_engine_id"] == "semantic_authority_reversal"
    assert payload["episodes"][0]["beat_signature"] == "resting-becomes-shift"
    assert payload["episodes"][0]["hook_mode"] == "specific_contradiction"
