#!/usr/bin/env -S uv run --script
# /// script
# requires-python = ">=3.12"
# dependencies = [
#     "pillow>=12.0",
#     "pydantic>=2.12",
#     "pytest>=9.0",
#     "typer>=0.20",
# ]
# ///

# ─── How to run ───
# uv run tests/test_instagram_link_contract.py
# ──────────────────

from __future__ import annotations

import json
import sys
from pathlib import Path

import pytest
from pydantic import ValidationError


SKILL_ROOT = Path(__file__).resolve().parents[1]
SCRIPTS = SKILL_ROOT / "scripts"
sys.path.insert(0, str(SCRIPTS))
type JsonScalar = str | int | float | bool | None
type JsonValue = JsonScalar | list[JsonValue] | dict[str, JsonValue]

from instagram_link_models import InstagramLinkAnalysisModel  # noqa: E402
from instagram_link_routing import resolve_instagram_link_route  # noqa: E402
from instagram_link_validation import (  # noqa: E402
    instagram_link_issues,
    requires_instagram_link_analysis,
)
from validate_episode import validate_episode  # noqa: E402


def _analysis_payload() -> dict[str, JsonValue]:
    return {
        "schema_version": "1.0",
        "source_platform": "instagram",
        "canonical_url": "https://www.instagram.com/p/AbC_123/",
        "post_type": "post",
        "access_status": "public",
        "accessed_at": "2026-07-21T12:00:00+09:00",
        "derived_topic": "마감 직전까지 미루는 직장인",
        "human_observation": "할 일이 많을수록 작은 정리부터 한다",
        "behavioral_contradiction": "중요한 일을 피하려고 더 바빠 보이는 일을 만든다",
        "humor_engine_candidates": ["self_rationalization_loop"],
        "hook_pattern": "중요한 일 대신 사소한 정리에 몰두한 손",
        "payoff_pattern": "정리는 완벽하지만 마감은 그대로인 결말",
        "excluded_elements": ["원문 대사", "창작자 신원", "브랜드와 로고"],
        "source_distance_check": {
            "result": "pass",
            "changed_dimensions": [
                "setting",
                "protagonist_goal",
                "escalation_path",
            ],
            "ending_reversal_reused": True,
        },
        "duplicate_check": {"matched_episode_ids": [], "result": "pass"},
        "safety_check": {"issues": [], "result": "pass"},
        "outcome": "pass",
    }


def _brief_payload(topic: str) -> dict[str, JsonValue]:
    directions: list[JsonValue] = []
    for identifier, engine in (
        ("A", "self_rationalization_loop"),
        ("B", "magnitude_mismatch"),
        ("C", "repetition_escalation"),
    ):
        directions.append(
            {
                "id": identifier,
                "premise": "중요한 일을 피하며 사소한 정리를 반복한다",
                "human_truth": "마감이 가까울수록 덜 중요한 일을 먼저 한다",
                "behavioral_contradiction": "일을 시작하려고 정리하다 일을 더 미룬다",
                "humor_engine_id": engine,
                "engine_explanation": "눈앞의 행동이 목표와 반대로 작동한다",
                "hook_promise": "완벽한 책상 위에 무엇이 빠졌을까?",
                "development_changes": [
                    "책상을 닦는다",
                    "펜을 줄 세운다",
                    "폴더 색을 맞춘다",
                    "마감 알림을 본다",
                ],
                "payoff_reversal": "정리는 끝났지만 문서는 비어 있다",
                "beat_signature": f"{engine}|avoidance|empty-document",
                "why_relatable": "미루기를 준비처럼 포장하는 순간",
            }
        )
    return {
        "schema_version": "1.1",
        "episode_id": "EP-001",
        "title": "완벽한 미루기",
        "topic": topic,
        "topic_origin": "instagram_link",
        "audience": "직장인",
        "tone": "가벼운 공감 유머",
        "characters": ["bgoon"],
        "directions": directions,
        "selected_direction": "A",
        "duplicate_check": {"matched_episode_ids": [], "result": "pass"},
        "sensitivity_check": {"issues": [], "result": "pass"},
        "selected_humor_engine_id": "self_rationalization_loop",
        "selected_beat_signature": "self_rationalization_loop|avoidance|empty-document",
        "hook_mode": "visual",
    }


def _write_json(path: Path, payload: dict[str, JsonValue]) -> None:
    _ = path.write_text(
        json.dumps(payload, ensure_ascii=False, indent=2) + "\n", encoding="utf-8"
    )


def test_link_route_is_ready_only_for_explicit_invocation_with_one_post_link() -> None:
    # Given: an explicit skill invocation and one direct post URL.
    request = "$instagram-toon https://www.instagram.com/p/AbC_123/?igsh=abc"

    # When: the coordinator resolves the dedicated link route.
    route = resolve_instagram_link_route(request, explicit_skill_invoked=True)

    # Then: it receives a canonical public-post URL.
    assert route.status == "ready"
    assert route.canonical_url == "https://www.instagram.com/p/AbC_123/"
    assert route.post_type == "post"


def test_link_route_does_not_activate_from_implicit_or_link_only_request() -> None:
    # Given: a link without an explicit skill invocation.
    request = "이 링크로 인스타툰 만들어줘 https://www.instagram.com/reel/AbC_123/"

    # When: the coordinator evaluates the link-specific trigger.
    route = resolve_instagram_link_route(request, explicit_skill_invoked=False)

    # Then: the dedicated agent is not selected.
    assert route.status == "not_requested"
    assert route.canonical_url is None


@pytest.mark.parametrize(
    ("request_text", "expected_message"),
    [
        (
            "$instagram-toon https://www.instagram.com/example_user/",
            "direct Instagram post or reel link",
        ),
        (
            "$instagram-toon https://www.instagram.com/p/one/ https://www.instagram.com/reel/two/",
            "exactly one link",
        ),
        (
            "$instagram-toon https://example.com/post",
            "direct Instagram post or reel link",
        ),
    ],
)
def test_link_route_requests_a_corrected_link_for_unsupported_input(
    request_text: str, expected_message: str
) -> None:
    # Given: an explicit invocation with an unsupported or ambiguous link.

    # When: the coordinator evaluates the link-specific trigger.
    route = resolve_instagram_link_route(request_text, explicit_skill_invoked=True)

    # Then: it asks for a corrected single direct link instead of falling back.
    assert route.status == "requires_user_input"
    assert expected_message in route.message


def test_source_analysis_allows_reusing_the_ending_reversal() -> None:
    # Given: a source analysis that transforms three story dimensions.
    payload = _analysis_payload()

    # When: the source artifact is parsed.
    analysis = InstagramLinkAnalysisModel.model_validate(payload)

    # Then: preserving the ending-reversal mechanism remains valid.
    assert analysis.source_distance_check.ending_reversal_reused is True


def test_source_analysis_rejects_too_little_transformation() -> None:
    # Given: a source analysis that changes only two non-ending dimensions.
    payload = _analysis_payload()
    distance = payload["source_distance_check"]
    assert isinstance(distance, dict)
    distance["changed_dimensions"] = ["setting", "protagonist_goal"]

    # When: the source artifact is parsed.

    # Then: it fails before story writing can start.
    with pytest.raises(ValidationError):
        _ = InstagramLinkAnalysisModel.model_validate(payload)


def test_instagram_link_episode_requires_matching_source_sidecar(tmp_path: Path) -> None:
    # Given: a link-derived episode brief.
    episode = tmp_path / "episodes" / "EP-001-link"
    episode.mkdir(parents=True)
    source = _analysis_payload()
    topic = str(source["derived_topic"])
    _write_json(episode / "brief.json", _brief_payload(topic))

    # When: source provenance is checked before and after the source artifact exists.
    required = requires_instagram_link_analysis(episode)
    before_source = instagram_link_issues(episode)
    _write_json(episode / "instagram-source.json", source)
    after_source = instagram_link_issues(episode)

    # Then: the link route requires its sidecar and accepts only the matching topic.
    assert required is True
    assert before_source == ()
    assert after_source == ()


def test_instagram_link_episode_rejects_a_mismatched_derived_topic(tmp_path: Path) -> None:
    # Given: a link-derived episode with a completed source sidecar.
    episode = tmp_path / "episodes" / "EP-001-link"
    episode.mkdir(parents=True)
    source = _analysis_payload()
    _write_json(episode / "brief.json", _brief_payload("다른 주제"))
    _write_json(episode / "instagram-source.json", source)

    # When: deterministic source validation compares both topics.
    issues = instagram_link_issues(episode)

    # Then: the episode cannot continue with a different story topic.
    assert len(issues) == 1
    assert "derived topic does not match brief topic" in issues[0]


def test_validator_requires_source_file_only_for_instagram_link_origin(
    tmp_path: Path,
) -> None:
    # Given: an otherwise unfinished Instagram-link episode without its source record.
    episode = tmp_path / "episodes" / "EP-001-link"
    episode.mkdir(parents=True)
    source = _analysis_payload()
    _write_json(episode / "brief.json", _brief_payload(str(source["derived_topic"])))

    # When: the deterministic validator resolves required files.
    _, issues = validate_episode(episode)

    # Then: the link-specific sidecar is a required artifact.
    assert any("instagram-source.json" in issue for issue in issues)


def test_source_analysis_rejects_private_or_login_required_result() -> None:
    # Given: a link analysis that could not read a public post.
    payload = _analysis_payload()
    payload["access_status"] = "requires_user_input"
    payload["outcome"] = "requires_user_input"

    # When: it is parsed as a completed episode artifact.

    # Then: the workflow stops rather than replacing it with another topic.
    with pytest.raises(ValidationError):
        _ = InstagramLinkAnalysisModel.model_validate(payload)
