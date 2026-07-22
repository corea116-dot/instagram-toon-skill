#!/usr/bin/env -S uv run --script
# /// script
# requires-python = ">=3.12"
# dependencies = [
#     "pillow>=12.0",
#     "pytest>=9.0",
#     "pydantic>=2.12",
#     "typer>=0.20",
# ]
# ///

# ─── How to run ───
# 1. Install uv (if not installed):
#      curl -LsSf https://astral.sh/uv/install.sh | sh
# 2. Run directly (no venv, no pip install needed):
#      uv run tests/test_topic_discovery_contract.py
# 3. Or make executable and run:
#      chmod +x tests/test_topic_discovery_contract.py && ./tests/test_topic_discovery_contract.py
# ──────────────────

from __future__ import annotations

from copy import deepcopy
import json
import os
from pathlib import Path
import subprocess
import sys
from typing import Literal, cast

import pytest
from pydantic import ValidationError


SKILL_ROOT = Path(__file__).resolve().parents[1]
SCRIPTS = SKILL_ROOT / "scripts"
sys.path.insert(0, str(SCRIPTS))

from episode_models import BriefModel, RichDirectionModel  # noqa: E402
from topic_research_models import RichTopicCandidateModel, TopicResearchModel  # noqa: E402
type JsonScalar = str | int | float | bool | None
type JsonValue = JsonScalar | list[JsonValue] | dict[str, JsonValue]
type TopicOrigin = Literal["user", "editorial_scout"]


def _write_json(path: Path, value: JsonValue) -> None:
    path.write_text(
        json.dumps(value, ensure_ascii=False, indent=2) + "\n", encoding="utf-8"
    )


def _make_episode(root: Path, topic_origin: TopicOrigin) -> Path:
    episode = root / "episodes" / "EP-001-자동-소재"
    episode.mkdir(parents=True)
    topic = "알람을 여러 번 미루는 직장인의 아침"
    directions: list[JsonValue] = [
        {
            "id": direction_id,
            "premise": f"알람을 미루는 아침 {direction_id}",
            "escalation": "준비 시간이 계속 줄어든다",
            "twist": "가방 대신 베개를 든다",
            "why_relatable": "출근 전 미루기의 악순환",
        }
        for direction_id in ("A", "B", "C")
    ]
    brief: dict[str, JsonValue] = {
        "schema_version": "1.0",
        "episode_id": "EP-001",
        "title": "알람과의 협상",
        "topic": topic,
        "topic_origin": topic_origin,
        "audience": "직장인",
        "tone": "가벼운 공감 유머",
        "characters": ["bgoon"],
        "directions": directions,
        "selected_direction": "A",
        "duplicate_check": {"matched_episode_ids": [], "result": "pass"},
        "sensitivity_check": {"issues": [], "result": "pass"},
    }
    panel_specs = (
        ("opening", "opening_hook"),
        ("development", "development_setup"),
        ("development", "development_escalation"),
        ("development", "development_complication"),
        ("development", "development_turn"),
        ("ending", "ending_payoff"),
    )
    panels: list[JsonValue] = []
    for number, (section, beat) in enumerate(panel_specs, start=1):
        panels.append(
            {
                "panel": number,
                "section": section,
                "beat": beat,
                "scene": f"아침 침실 장면 {number}",
                "expression": "졸린 표정",
                "action": "휴대폰 알람을 확인한다",
                "props": ["휴대폰", "이불"],
                "background": "단순한 침실",
                "camera": "미디엄 숏",
                "dialogue": [
                    {
                        "speaker": "bgoon",
                        "text": "딱 5분만",
                        "x": 70,
                        "y": 65,
                        "width": 940,
                        "height": 260,
                    }
                ],
            }
        )
    _write_json(episode / "brief.json", brief)
    _write_json(
        episode / "script.json",
        {
            "schema_version": "1.0",
            "episode_id": "EP-001",
            "title": "알람과의 협상",
            "panels": panels,
        },
    )
    (episode / "caption.txt").write_text("5분만 더의 결말.\n", encoding="utf-8")
    return episode


def _write_topic_research(episode: Path) -> None:
    topic = "알람을 여러 번 미루는 직장인의 아침"
    candidates: list[JsonValue] = []
    totals = (84, 80, 78, 76, 75)
    for index, total in enumerate(totals, start=1):
        candidates.append(
            {
                "id": f"candidate-{index}",
                "topic": topic if index == 1 else f"직장인의 일상 소재 {index}",
                "observation": "공감 가능한 일상 마찰",
                "story_seed": "짧은 반전으로 끝나는 일상 코미디",
                "source_ids": ["source-1", "source-2"],
                "scores": {
                    "relatability": 25,
                    "humor": 25,
                    "opening_hook": 16,
                    "novelty": 9,
                    "production_fit": total - 75,
                    "total": total,
                },
            }
        )
    _write_json(
        episode / "topic-research.json",
        {
            "schema_version": "1.0",
            "source_mode": "public_web",
            "search_window_days": 30,
            "sources": [
                {
                    "id": "source-1",
                    "kind": "public_page",
                    "url": "https://example.com/one",
                    "title": "공개 신호 하나",
                    "observation": "일상적인 미루기 소재",
                    "accessed_at": "2026-07-20T00:00:00+00:00",
                },
                {
                    "id": "source-2",
                    "kind": "public_page",
                    "url": "https://example.com/two",
                    "title": "공개 신호 둘",
                    "observation": "출근 전 공감 소재",
                    "accessed_at": "2026-07-20T00:00:00+00:00",
                },
            ],
            "candidates": candidates,
            "selected_candidate_id": "candidate-1",
            "selected_topic": topic,
            "selection_reason": "가장 높은 기준 점수를 받은 후보",
            "fallback_reason": None,
        },
    )


def _upgrade_editorial_episode_to_v11(episode: Path) -> None:
    brief_path = episode / "brief.json"
    brief = json.loads(brief_path.read_text(encoding="utf-8"))
    assert isinstance(brief, dict)
    engines = (
        "semantic_authority_reversal",
        "magnitude_mismatch",
        "self_rationalization_loop",
    )
    brief["schema_version"] = "1.1"
    brief["directions"] = [
        {
            "id": identifier,
            "premise": "알람과 협상하는 아침",
            "human_truth": "시간이 없을수록 한 번 더 미룬다",
            "behavioral_contradiction": "시간을 아끼려다 준비를 더 미룬다",
            "humor_engine_id": engines[index],
            "engine_explanation": "일상 행동의 기대를 짧은 반전으로 뒤집는다",
            "hook_promise": "알람을 끈 손에 무엇이 들렸을까?",
            "development_changes": ["알람을 끈다", "다시 눕는다", "시간을 확인한다", "가방을 찾는다"],
            "payoff_reversal": "가방 대신 베개를 든다",
            "beat_signature": f"{engines[index]}|alarm|pillow-bag",
            "why_relatable": "출근 전 미루기의 악순환",
        }
        for index, identifier in enumerate(("A", "B", "C"))
    ]
    brief["selected_humor_engine_id"] = engines[0]
    brief["selected_beat_signature"] = f"{engines[0]}|alarm|pillow-bag"
    brief["hook_mode"] = "visual"
    _write_json(brief_path, brief)

    research_path = episode / "topic-research.json"
    research = json.loads(research_path.read_text(encoding="utf-8"))
    assert isinstance(research, dict)
    research["schema_version"] = "1.1"
    candidates = research["candidates"]
    assert isinstance(candidates, list)
    candidate_engines = (
        "magnitude_mismatch",
        "semantic_authority_reversal",
        "self_rationalization_loop",
        "magnitude_mismatch",
        "semantic_authority_reversal",
    )
    for index, candidate in enumerate(candidates):
        assert isinstance(candidate, dict)
        engine = candidate_engines[index]
        candidate.update(
            {
                "source_signal": "공개 출처가 반복적으로 지지한 출근 전 행동",
                "source_relevance": "두 출처가 같은 구체적 행동을 뒷받침한다",
                "human_observation": "준비 시간이 줄수록 포기 항목이 늘어난다",
                "behavioral_contradiction": "시간을 아끼려다 결정적인 물건을 놓친다",
                "humor_engine_id": engine,
                "engine_explanation": "작은 시간 절약이 큰 실수로 뒤집힌다",
                "hook_seed": "급하게 준비한 인물",
                "payoff_seed": "필요한 물건이 다른 것이다",
                "beat_signature": f"{engine}|alarm|wrong-item-{index}",
                "eligibility": True,
                "gate_results": {
                    "source_relevance": True,
                    "human_observation": True,
                    "behavioral_contradiction": True,
                    "humor_engine": True,
                    "hook_seed": True,
                    "payoff_seed": True,
                    "safety": True,
                    "duplicate": True,
                },
            }
        )
    _write_json(research_path, research)


def _run(script: str, *arguments: str) -> subprocess.CompletedProcess[str]:
    environment = os.environ | {"PYTHONDONTWRITEBYTECODE": "1"}
    return subprocess.run(
        [sys.executable, str(SCRIPTS / script), *arguments],
        check=False,
        capture_output=True,
        text=True,
        env=environment,
    )


def test_validation_requires_research_when_editorial_scout_selected_topic(
    tmp_path: Path,
) -> None:
    episode = _make_episode(tmp_path, "editorial_scout")
    composed = _run("compose_episode.py", "--episode-dir", str(episode), "--mock")
    assert composed.returncode == 0, composed.stderr

    validated = _run("validate_episode.py", "--episode-dir", str(episode))

    assert validated.returncode != 0
    assert "topic-research.json" in validated.stderr


def test_validation_accepts_matched_research_when_editorial_scout_selected_topic(
    tmp_path: Path,
) -> None:
    episode = _make_episode(tmp_path, "editorial_scout")
    _write_topic_research(episode)
    composed = _run("compose_episode.py", "--episode-dir", str(episode), "--mock")
    assert composed.returncode == 0, composed.stderr

    validated = _run("validate_episode.py", "--episode-dir", str(episode))

    assert validated.returncode != 0
    assert "schema 1.1" in validated.stderr


def test_validation_accepts_matched_v11_research_for_editorial_scout(
    tmp_path: Path,
) -> None:
    episode = _make_episode(tmp_path, "editorial_scout")
    _write_topic_research(episode)
    _upgrade_editorial_episode_to_v11(episode)
    composed = _run("compose_episode.py", "--episode-dir", str(episode), "--mock")
    assert composed.returncode == 0, composed.stderr

    validated = _run("validate_episode.py", "--episode-dir", str(episode))

    assert validated.returncode == 0, validated.stderr


def test_validation_rejects_an_uncited_public_web_candidate(tmp_path: Path) -> None:
    episode = _make_episode(tmp_path, "editorial_scout")
    _write_topic_research(episode)
    _upgrade_editorial_episode_to_v11(episode)
    research_path = episode / "topic-research.json"
    research = json.loads(research_path.read_text(encoding="utf-8"))
    assert isinstance(research, dict)
    candidates = research["candidates"]
    assert isinstance(candidates, list)
    candidate = candidates[-1]
    assert isinstance(candidate, dict)
    candidate["source_ids"] = []
    _write_json(research_path, research)
    composed = _run("compose_episode.py", "--episode-dir", str(episode), "--mock")
    assert composed.returncode == 0, composed.stderr

    validated = _run("validate_episode.py", "--episode-dir", str(episode))

    assert validated.returncode != 0
    assert "public-web candidates require source ids" in validated.stderr


def test_v11_rejects_selected_candidate_with_lower_public_engagement_priority(
    tmp_path: Path,
) -> None:
    # Given: two eligible candidates with visible public engagement evidence.
    episode = _make_episode(tmp_path, "editorial_scout")
    _write_topic_research(episode)
    _upgrade_editorial_episode_to_v11(episode)
    research_path = episode / "topic-research.json"
    research = json.loads(research_path.read_text(encoding="utf-8"))
    assert isinstance(research, dict)
    sources = research["sources"]
    candidates = research["candidates"]
    assert isinstance(sources, list)
    assert isinstance(candidates, list)
    first_source = sources[0]
    second_source = sources[1]
    first_candidate = candidates[0]
    second_candidate = candidates[1]
    assert isinstance(first_source, dict)
    assert isinstance(second_source, dict)
    assert isinstance(first_candidate, dict)
    assert isinstance(second_candidate, dict)
    first_source["engagement"] = {"likes": 120, "comments": 8}
    second_source["engagement"] = {"likes": 1800, "comments": 140}
    first_candidate["engagement_priority"] = 20
    second_candidate["engagement_priority"] = 90
    _write_json(research_path, research)

    # When: the higher-total but lower-engagement candidate remains selected.
    # Then: the structured record rejects that selection.
    with pytest.raises(ValidationError, match="highest eligible engagement priority"):
        _ = TopicResearchModel.model_validate(research)


def test_validation_skips_research_when_user_supplied_topic(tmp_path: Path) -> None:
    episode = _make_episode(tmp_path, "user")
    composed = _run("compose_episode.py", "--episode-dir", str(episode), "--mock")
    assert composed.returncode == 0, composed.stderr

    validated = _run("validate_episode.py", "--episode-dir", str(episode))

    assert validated.returncode == 0, validated.stderr


def test_prompt_manifests_start_with_primary_style_references_on_full_and_targeted_compose(
    tmp_path: Path,
) -> None:
    episode = _make_episode(tmp_path, "user")
    composed = _run("compose_episode.py", "--episode-dir", str(episode), "--mock")
    assert composed.returncode == 0, composed.stderr
    expected = [
        "assets/references/styles/screenshots-2026-07-19/스크린샷 2026-07-19 오후 4.07.38.png",
        "assets/references/styles/screenshots-2026-07-19/스크린샷 2026-07-19 오후 4.07.58.png",
        "assets/references/styles/screenshots-2026-07-19/스크린샷 2026-07-19 오후 4.08.23.png",
    ]
    for number in range(1, 7):
        prompt = json.loads((episode / "prompts" / f"panel-{number}.json").read_text(encoding="utf-8"))
        assert prompt["reference_images"][:3] == expected
    panel_path = episode / "prompts" / "panel-4.json"
    panel = json.loads(panel_path.read_text(encoding="utf-8"))
    panel["reference_images"].append("assets/references/characters/bgoon/bgoon-1.png")
    _write_json(panel_path, panel)
    regenerated = _run(
        "compose_episode.py", "--episode-dir", str(episode), "--mock", "--panel", "4"
    )
    assert regenerated.returncode == 0, regenerated.stderr
    prompt = json.loads(panel_path.read_text(encoding="utf-8"))
    assert prompt["revision"] == 1
    assert prompt["reference_images"] == expected + [
        "assets/references/characters/bgoon/bgoon-1.png"
    ]


def test_prompt_manifests_use_only_first_three_configured_primary_references(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    import compose_episode

    visual_style = json.loads((SKILL_ROOT / "memory" / "visual-style.json").read_text(encoding="utf-8"))
    references = visual_style["reference_policy"]["primary_reference_images"]
    assert isinstance(references, list)
    visual_style["reference_policy"]["primary_reference_images"] = references + [references[0]]
    configured_style = tmp_path / "visual-style.json"
    _write_json(configured_style, visual_style)
    monkeypatch.setattr(compose_episode, "VISUAL_STYLE_PATH", configured_style)
    episode = _make_episode(tmp_path, "user")

    _ = compose_episode.compose(
        compose_episode.ComposeOptions(episode_dir=episode, mock=True, panel=None)
    )

    expected = references[:3]
    prompt_path = episode / "prompts" / "panel-4.json"
    prompt = json.loads(prompt_path.read_text(encoding="utf-8"))
    assert prompt["reference_images"] == expected
    prompt["reference_images"].append("assets/references/characters/bgoon/bgoon-1.png")
    _write_json(prompt_path, prompt)

    _ = compose_episode.compose(
        compose_episode.ComposeOptions(episode_dir=episode, mock=True, panel=4)
    )

    regenerated = json.loads(prompt_path.read_text(encoding="utf-8"))
    assert regenerated["reference_images"] == expected + [
        "assets/references/characters/bgoon/bgoon-1.png"
    ]


def test_v11_story_quality_contract_requires_complete_directions_and_eligible_selection() -> None:
    engines = (
        "semantic_authority_reversal",
        "magnitude_mismatch",
        "self_rationalization_loop",
    )
    directions = [
        {
            "id": identifier,
            "premise": "침대가 퇴근을 승인하는 이야기",
            "human_truth": "쉬려다 휴대폰으로 시간을 더 쓴다",
            "behavioral_contradiction": "쉬려고 누웠지만 더 오래 일상을 미룬다",
            "humor_engine_id": engines[index],
            "engine_explanation": "침대가 상사처럼 퇴근을 승인한다",
            "hook_promise": "침대가 왜 출근 체크를 하지?",
            "development_changes": ["눕는다", "휴대폰을 켠다", "체크인을 받는다", "승인을 기다린다"],
            "payoff_reversal": "침대가 퇴근을 승인한다",
            "beat_signature": "resting-becomes-shift",
            "why_relatable": "퇴근 후 휴대폰을 보는 습관",
        }
        for index, identifier in enumerate(("A", "B", "C"))
    ]
    brief: dict[str, object] = {
        "schema_version": "1.1",
        "episode_id": "EP-001",
        "title": "퇴근 승인",
        "topic": "퇴근 후 휴대폰",
        "audience": "직장인",
        "tone": "공감 유머",
        "characters": ["bgoon"],
        "directions": directions,
        "selected_direction": "A",
        "duplicate_check": {"matched_episode_ids": [], "result": "pass"},
        "sensitivity_check": {"issues": [], "result": "pass"},
        "selected_humor_engine_id": "semantic_authority_reversal",
        "selected_beat_signature": "resting-becomes-shift",
        "hook_mode": "specific_contradiction",
    }
    validated_brief = BriefModel.model_validate(brief)
    assert validated_brief.schema_version == "1.1"
    for field in (
        "human_truth",
        "behavioral_contradiction",
        "humor_engine_id",
        "engine_explanation",
        "hook_promise",
        "payoff_reversal",
        "beat_signature",
    ):
        invalid_brief = deepcopy(brief)
        directions = cast(list[dict[str, object]], invalid_brief["directions"])
        direction = directions[0]
        direction.pop(field)
        with pytest.raises(ValidationError):
            BriefModel.model_validate(invalid_brief)
    invalid_brief = deepcopy(brief)
    directions = cast(list[dict[str, object]], invalid_brief["directions"])
    direction = directions[0]
    direction["development_changes"] = ["하나", "둘", "셋"]
    with pytest.raises(ValidationError):
        BriefModel.model_validate(invalid_brief)
    for field in (
        "human_truth",
        "behavioral_contradiction",
        "engine_explanation",
        "hook_promise",
        "payoff_reversal",
        "beat_signature",
        "why_relatable",
    ):
        for blank_value in ("", " \t\n "):
            invalid_brief = deepcopy(brief)
            directions = cast(list[dict[str, object]], invalid_brief["directions"])
            directions[0][field] = blank_value
            with pytest.raises(ValidationError):
                BriefModel.model_validate(invalid_brief)
    for change_index in range(4):
        for blank_value in ("", " \t\n "):
            invalid_brief = deepcopy(brief)
            directions = cast(list[dict[str, object]], invalid_brief["directions"])
            development_changes = cast(list[str], directions[0]["development_changes"])
            development_changes[change_index] = blank_value
            with pytest.raises(ValidationError):
                BriefModel.model_validate(invalid_brief)

    candidates = [
        {
            "id": f"candidate-{index}",
            "topic": f"소재 {index}",
            "observation": "퇴근 뒤 휴대폰을 본다",
            "story_seed": "침대가 퇴근을 연장한다",
            "source_ids": ["source-1", "source-2"],
            "source_signal": "공개 출처가 같은 행동을 뒷받침한다",
            "source_relevance": "두 출처가 같은 행동을 뒷받침한다",
            "human_observation": "침대에서 휴대폰을 켠다",
            "behavioral_contradiction": "쉬려다 더 오래 미룬다",
            "humor_engine_id": engines[(index - 1) % len(engines)],
            "engine_explanation": "관찰의 기대를 짧은 행동으로 뒤집는다",
            "hook_seed": "침대가 왜 출근 체크를 하지?",
            "payoff_seed": "침대가 퇴근을 승인한다",
            "beat_signature": f"engine-{index}|payoff",
            "eligibility": index != 1,
            "gate_results": {
                "source_relevance": index != 1,
                "human_observation": index != 1,
                "behavioral_contradiction": index != 1,
                "humor_engine": index != 1,
                "hook_seed": index != 1,
                "payoff_seed": index != 1,
                "safety": index != 1,
                "duplicate": index != 1,
            },
            "scores": {"relatability": 25, "humor": 25, "opening_hook": 16, "novelty": 9, "production_fit": 10 - index, "total": 85 - index},
        }
        for index in range(1, 6)
    ]
    research: dict[str, object] = {
        "schema_version": "1.1", "source_mode": "public_web", "search_window_days": 30,
        "sources": [
            {"id": "source-1", "kind": "public_page", "url": "https://example.com/one", "title": "신호 하나", "observation": "관찰", "accessed_at": "2026-07-20T00:00:00+00:00"},
            {"id": "source-2", "kind": "public_page", "url": "https://example.com/two", "title": "신호 둘", "observation": "관찰", "accessed_at": "2026-07-20T00:00:00+00:00"},
        ],
        "candidates": candidates, "selected_candidate_id": "candidate-2", "selected_topic": "소재 2", "selection_reason": "가장 높은 적격 후보",
    }
    validated_research = TopicResearchModel.model_validate(research)
    assert validated_research.selected_candidate_id == "candidate-2"
    for field in (
        "source_relevance",
        "human_observation",
        "behavioral_contradiction",
        "humor_engine_id",
        "hook_seed",
        "payoff_seed",
        "eligibility",
        "gate_results",
    ):
        invalid_research = deepcopy(research)
        candidates = cast(list[dict[str, object]], invalid_research["candidates"])
        candidate = candidates[0]
        candidate.pop(field)
        with pytest.raises(ValidationError):
            TopicResearchModel.model_validate(invalid_research)
    for field in (
        "source_signal",
        "source_relevance",
        "human_observation",
        "behavioral_contradiction",
        "engine_explanation",
        "hook_seed",
        "payoff_seed",
        "beat_signature",
    ):
        for blank_value in ("", " \t\n "):
            invalid_research = deepcopy(research)
            candidates = cast(list[dict[str, object]], invalid_research["candidates"])
            candidates[1][field] = blank_value
            with pytest.raises(ValidationError):
                TopicResearchModel.model_validate(invalid_research)
    research["selected_candidate_id"] = "candidate-1"
    research["selected_topic"] = "소재 1"
    with pytest.raises(ValidationError, match="eligible"):
        TopicResearchModel.model_validate(research)


def test_v11_strips_editorial_evidence_in_docs_shaped_records(tmp_path: Path) -> None:
    episode = _make_episode(tmp_path, "editorial_scout")
    _write_topic_research(episode)
    _upgrade_editorial_episode_to_v11(episode)

    research = json.loads((episode / "topic-research.json").read_text(encoding="utf-8"))
    assert isinstance(research, dict)
    candidates = research["candidates"]
    assert isinstance(candidates, list)
    candidate = candidates[0]
    assert isinstance(candidate, dict)
    candidate["source_signal"] = "  공개 출처가 지지한 출근 전 행동  "
    candidate["hook_seed"] = "  급하게 준비한 인물  "
    validated_research = TopicResearchModel.model_validate(research)
    validated_candidate = validated_research.candidates[0]
    assert isinstance(validated_candidate, RichTopicCandidateModel)
    assert validated_candidate.source_signal == "공개 출처가 지지한 출근 전 행동"
    assert validated_candidate.hook_seed == "급하게 준비한 인물"

    brief = json.loads((episode / "brief.json").read_text(encoding="utf-8"))
    assert isinstance(brief, dict)
    directions = brief["directions"]
    assert isinstance(directions, list)
    direction = directions[0]
    assert isinstance(direction, dict)
    direction["human_truth"] = "  시간이 없을수록 한 번 더 미룬다  "
    development_changes = direction["development_changes"]
    assert isinstance(development_changes, list)
    development_changes[0] = "  알람을 끈다  "
    validated_brief = BriefModel.model_validate(brief)
    validated_direction = validated_brief.directions[0]
    assert isinstance(validated_direction, RichDirectionModel)
    assert validated_direction.human_truth == "시간이 없을수록 한 번 더 미룬다"
    assert validated_direction.development_changes[0] == "알람을 끈다"


def test_v10_models_remain_permissive_for_legacy_editorial_strings() -> None:
    legacy_brief = {
        "schema_version": "1.0",
        "episode_id": "EP-legacy",
        "title": "",
        "topic": "",
        "audience": "",
        "tone": "",
        "characters": [],
        "directions": [
            {
                "id": identifier,
                "premise": " \t\n ",
                "escalation": " \t\n ",
                "twist": " \t\n ",
                "why_relatable": " \t\n ",
            }
            for identifier in ("A", "B", "C")
        ],
        "selected_direction": "A",
        "duplicate_check": {"matched_episode_ids": [], "result": "pass"},
        "sensitivity_check": {"issues": [], "result": "pass"},
    }
    assert BriefModel.model_validate(legacy_brief).schema_version == "1.0"

    legacy_research = {
        "schema_version": "1.0",
        "source_mode": "local_fallback",
        "search_window_days": 30,
        "sources": [],
        "candidates": [
            {
                "id": f"candidate-{index}",
                "topic": " \t\n ",
                "observation": " \t\n ",
                "story_seed": " \t\n ",
                "source_ids": [],
                "scores": {
                    "relatability": 25,
                    "humor": 25,
                    "opening_hook": 16,
                    "novelty": 9,
                    "production_fit": 10 - index,
                    "total": 85 - index,
                },
            }
            for index in range(1, 6)
        ],
        "selected_candidate_id": "candidate-1",
        "selected_topic": " \t\n ",
        "selection_reason": " \t\n ",
        "fallback_reason": "web unavailable",
    }
    assert TopicResearchModel.model_validate(legacy_research).schema_version == "1.0"


if __name__ == "__main__":
    raise SystemExit(pytest.main([__file__, "-q"]))
