from __future__ import annotations

import json
import sys
from pathlib import Path

import pytest
from pydantic import ValidationError

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "scripts"))

from episode_models import PRIMARY_HUMOR_ENGINE_IDS
from keyword_history import next_keyword_type
from keyword_models import KeywordEvidence, KeywordResearch
from keyword_selection import select_topic


def synthetic_evidence() -> KeywordEvidence:
    """Synthetic, offline-only evidence; never represents observed search demand."""
    candidates = []
    for index in range(5):
        candidates.append(
            {
                "id": str(index),
                "keyword": f"테스트 키워드 {index}",
                "topic": f"테스트 주제 {index}",
                "category": "personal_finance",
                "keyword_type": "evergreen",
                "demand_reason": "합성 테스트 장기 수요",
                "official_source_ids": ["official"],
                "source_ids": ["naver", "google", "official"],
                "observation": "조건을 읽지 않고 계산부터 한다",
                "story_seed": "계산기가 서류를 요구한다",
                "source_signal": "합성 검색 증거",
                "source_relevance": "초년생 돈 관리",
                "human_observation": "이득부터 센다",
                "behavioral_contradiction": "조건은 안 읽는다",
                "humor_engine_id": PRIMARY_HUMOR_ENGINE_IDS[index],
                "engine_explanation": "계산기가 심사한다",
                "hook_seed": "나만 못 받는 돈?",
                "payoff_seed": "계산기부터 서류심사",
                "beat_signature": f"합성-{index}",
                "eligibility": True,
                "gate_results": {
                    key: True
                    for key in (
                        "source_relevance",
                        "human_observation",
                        "behavioral_contradiction",
                        "humor_engine",
                        "hook_seed",
                        "payoff_seed",
                        "safety",
                        "duplicate",
                    )
                },
                "scores": {
                    "relatability": 25,
                    "humor": 25,
                    "opening_hook": 15,
                    "novelty": 8,
                    "production_fit": 8,
                    "total": 81,
                },
            }
        )
    sources = [
        {
            "id": platform,
            "kind": platform,
            "url": f"https://{platform}.example.test/evidence",
            "title": "SYNTHETIC TEST ONLY",
            "observation": "합성 테스트 수치",
            "accessed_at": "2026-09-14T09:00:00+09:00",
        }
        for platform in ("naver", "google", "official")
    ]
    batches = [
        {
            "platform": platform,
            "method": "monthly_volume",
            "comparison_key": "same-settings",
            "window_start": "2026-08-01",
            "window_end": "2026-08-31",
            "geo": "KR",
            "values": [
                {"candidate_id": str(index), "value": value, "source_id": platform,
                 "pc_searches": value, "mobile_searches": 0}
                for index, value in enumerate(values)
            ],
        }
        for platform, values in (
            ("naver", [500, 400, 300, 200, 100]),
            ("google", [10, 20, 30, 40, 50]),
        )
    ]
    return KeywordEvidence.model_validate(
        {
            "schema_version": "1.0",
            "researched_on": "2026-09-14",
            "sources": sources,
            "candidates": candidates,
            "batches": batches,
            "collection_notes": "Synthetic test; not live keyword findings.",
        }
    )


def test_weighted_ranks_and_trending_fallback() -> None:
    result = select_topic(synthetic_evidence(), "trending")
    assert result.selected_id == "0"
    assert result.effective_type == "evergreen"
    assert [row.total for row in result.scores] == [60, 55, 50, 45, 40]
    assert result.evidence_label == "exact_monthly"


def test_missing_platform_holds_instead_of_inventing_volume() -> None:
    data = synthetic_evidence().model_dump(mode="json")
    data["batches"] = data["batches"][:1]
    result = select_topic(KeywordEvidence.model_validate(data), "evergreen")
    assert result.status == "hold"
    assert result.selected_id is None


def test_partial_monthly_uses_complete_relative_batch() -> None:
    data = synthetic_evidence().model_dump(mode="json")
    original = synthetic_evidence().batches[0]
    relative = original.model_copy(
        update={
            "method": "relative_index",
            "values": tuple(
                item.model_copy(update={"value": 100 - index * 10})
                for index, item in enumerate(original.values)
            ),
        }
    )
    data["batches"][0]["values"] = data["batches"][0]["values"][:2]
    data["batches"].append(relative.model_dump(mode="json"))
    result = select_topic(KeywordEvidence.model_validate(data), "evergreen")
    assert result.bases[0].method == "relative_index"
    assert result.evidence_label == "relative_proxy"


def test_ties_are_average_rank_and_zero_volume_cannot_win() -> None:
    data = synthetic_evidence().model_dump(mode="json")
    for batch in data["batches"]:
        for item in batch["values"]:
            item["value"] = 0
    result = select_topic(KeywordEvidence.model_validate(data), "evergreen")
    assert result.status == "hold"


def test_official_deadline_is_not_claimed_to_be_rising_search() -> None:
    data = synthetic_evidence().model_dump(mode="json")
    data["candidates"][2].update(
        keyword_type="trending", event_kind="deadline", event_date="2026-09-20"
    )
    result = select_topic(KeywordEvidence.model_validate(data), "trending")
    assert result.selected_id == "2"
    assert "official_event" in result.reason


def test_expired_deadline_does_not_trigger_trending() -> None:
    data = synthetic_evidence().model_dump(mode="json")
    data["candidates"][0].update(
        keyword_type="trending", event_kind="deadline", event_date="2026-09-13"
    )
    result = select_topic(KeywordEvidence.model_validate(data), "trending")
    assert result.selected_id == "1"
    assert result.effective_type == "evergreen"


def test_research_rejects_tampered_winner() -> None:
    evidence = synthetic_evidence()
    decision = select_topic(evidence, "evergreen")
    payload = {
        "schema_version": "1.2",
        "evidence": evidence.model_dump(mode="json"),
        "decision": decision.model_dump(mode="json"),
    }
    payload["decision"]["selected_id"] = "4"
    with pytest.raises(ValidationError, match="recomputed"):
        KeywordResearch.model_validate(payload)


def test_rotation_counts_unique_successes_only(tmp_path: Path) -> None:
    path = tmp_path / "history.json"
    path.write_text(
        json.dumps(
            {
                "schema_version": "1.1",
                "episodes": [
                    {"episode_id": "EP-001", "status": "draft"},
                    {
                        "episode_id": "EP-002",
                        "keyword_selection": {
                            "requested_type": "trending",
                            "effective_type": "evergreen",
                            "review_state": "review_pending",
                            "research_sha256": "a" * 64,
                        },
                    },
                    {
                        "episode_id": "EP-002",
                        "keyword_selection": {
                            "requested_type": "trending",
                            "effective_type": "evergreen",
                            "review_state": "review_pending",
                            "research_sha256": "a" * 64,
                        },
                    },
                ],
            }
        ),
        encoding="utf-8",
    )
    assert next_keyword_type(path) == "evergreen"


def test_future_or_stale_source_cannot_enter_evidence() -> None:
    data = synthetic_evidence().model_dump(mode="json")
    data["sources"][0]["accessed_at"] = "2026-10-01T09:00:00+09:00"
    with pytest.raises(ValidationError):
        KeywordEvidence.model_validate(data)


def test_equal_positive_demand_has_neutral_tied_ranks() -> None:
    data = synthetic_evidence().model_dump(mode="json")
    for batch in data["batches"]:
        for item in batch["values"]:
            item["value"] = 100
    result = select_topic(KeywordEvidence.model_validate(data), "evergreen")
    assert [row.total for row in result.scores] == [50, 50, 50, 50, 50]
    assert [row.rank for row in result.scores] == [1, 1, 1, 1, 1]


def test_related_rank_orders_lower_position_first() -> None:
    data = synthetic_evidence().model_dump(mode="json")
    for batch in data["batches"]:
        batch["method"] = "related_rank"
    result = select_topic(KeywordEvidence.model_validate(data), "evergreen")
    assert result.selected_id == "4"
    assert result.evidence_label == "relative_proxy"


def test_measured_rise_beats_event_fallback_tier() -> None:
    data = synthetic_evidence().model_dump(mode="json")
    data["candidates"][0].update(
        keyword_type="trending", event_kind="deadline", event_date="2026-09-20"
    )
    data["candidates"][3]["keyword_type"] = "trending"
    batch = data["batches"][0]
    batch.update(previous_window_start="2026-07-01", previous_window_end="2026-07-31")
    batch["values"][3]["previous_value"] = 10
    result = select_topic(KeywordEvidence.model_validate(data), "trending")
    assert result.selected_id == "3"
    assert result.reason.startswith("rising:")


def test_high_demand_cannot_override_story_gate() -> None:
    data = synthetic_evidence().model_dump(mode="json")
    data["candidates"][0]["scores"].update(humor=10, total=66)
    result = select_topic(KeywordEvidence.model_validate(data), "evergreen")
    assert result.selected_id == "1"
    assert result.scores[0].rejection_reason == "story/safety/duplicate gate failed"
