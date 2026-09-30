"""Synthetic record tests; fixtures do not claim a real financial source review."""

from __future__ import annotations

import json
import subprocess
import sys
from pathlib import Path

import pytest
from pydantic import ValidationError

SCRIPTS = Path(__file__).resolve().parents[1] / "scripts"
sys.path.insert(0, str(SCRIPTS))

from content_review import (
    ContentReviewModel,
    content_review_issues,
    file_sha256,
    layout_sha256,
    semantic_content_sha256,
)
from episode_models import BriefModel, EpisodeScriptModel
from information_lock import content_lock_issues
from layout_preflight import layout_preflight_issues


def write_json(path: Path, payload: dict) -> None:
    path.write_text(
        json.dumps(payload, ensure_ascii=False, indent=2) + "\n", encoding="utf-8"
    )


def recorded_issues(episode: Path) -> tuple[str, ...]:
    issues = content_review_issues(episode)
    (episode / "content-review-issues.txt").write_text(
        "\n".join(issues) or "PASS\n", encoding="utf-8"
    )
    return issues


def informational_episode(
    root: Path, layout: tuple[int, ...] = (1, 1, 1, 1, 1)
) -> Path:
    root.mkdir(parents=True, exist_ok=True)
    count = sum(layout)
    brief = {
        "schema_version": "1.2",
        "content_type": "informational",
        "episode_id": "EP-999",
        "title": "테스트 상품의 조건",
        "topic": "테스트 상품",
        "audience": "사회초년생",
        "tone": "정보",
        "characters": ["bgoon"],
        "output_layout": layout,
        "question_answer": {
            "search_keyword": "테스트 상품",
            "reader_question": "어떤 상품이고 무엇을 확인해야 할까?",
            "one_line_answer": "혜택뿐 아니라 조건과 손실 위험을 확인한다.",
            "required_facts": [
                {
                    "id": "identity",
                    "claim": "테스트용 투자 상품",
                    "category": "identity",
                    "sources": [
                        {
                            "url": "https://example.org/fixture",
                            "title": "합성 테스트 자료",
                            "publisher": "테스트 작성자",
                            "checked_on": "2026-09-29",
                            "supporting_excerpt": "테스트용 투자 상품",
                        }
                    ],
                },
                {
                    "id": "risk",
                    "claim": "손실 가능성을 확인",
                    "category": "risk",
                    "sources": [
                        {
                            "url": "https://example.org/fixture",
                            "title": "합성 테스트 자료",
                            "publisher": "테스트 작성자",
                            "checked_on": "2026-09-29",
                            "supporting_excerpt": "손실 가능성을 확인",
                        }
                    ],
                },
            ],
            "reader_action": "공식 설명서에서 조건을 확인한다.",
            "out_of_scope": ["가입 권유"],
        },
        "directions": [
            {
                "id": "A",
                "premise": "상품의 조건을 확인한다",
                "hook_promise": "무엇을 확인할까?",
                "development_changes": [f"새로운 정보 {n}" for n in range(count - 2)],
                "ending_answer": "손실 가능성을 확인한다",
            }
        ],
        "selected_direction": "A",
        "duplicate_check": {"matched_episode_ids": [], "result": "pass"},
        "sensitivity_check": {"issues": [], "result": "pass"},
    }
    script = {
        "schema_version": "1.1",
        "episode_id": "EP-999",
        "title": brief["title"],
        "output_layout": layout,
        "panels": [
            {
                "panel": n,
                "section": "opening"
                if n == 1
                else "ending"
                if n == count
                else "development",
                "beat": "opening_hook"
                if n == 1
                else "ending_payoff"
                if n == count
                else "development",
                "scene": "설명서를 읽는 장면",
                "expression": "집중",
                "action": "설명서를 읽는다",
                "props": ["설명서"],
                "background": "단순한 방",
                "camera": "미디엄 숏",
                "dialogue": [
                    {
                        "speaker": "bgoon",
                        "text": "테스트용 투자 상품"
                        if n == 1
                        else "손실 가능성을 확인",
                        "x": 70,
                        "y": 65,
                        "width": 940,
                        "height": 260,
                    }
                ],
            }
            for n in range(1, count + 1)
        ],
    }
    write_json(root / "brief.json", brief)
    write_json(root / "script.json", script)
    (root / "caption.txt").write_text("합성 테스트 에피소드\n", encoding="utf-8")
    write_json(root / "content-review.json", review_payload(root))
    return root


def review_payload(root: Path) -> dict:
    return {
        "schema_version": "1.0",
        "episode_id": "EP-999",
        "writer_id": "test-writer",
        "reviewer_id": "test-reviewer",
        "brief_sha256": file_sha256(root / "brief.json"),
        "script_sha256": file_sha256(root / "script.json"),
        "stages": ["blind_read", "card_source_checks"],
        "blind_read": {
            "completed_at": "2026-09-29T01:00:00+09:00",
            "topic_understood": "테스트용 상품",
            "learned": "손실 가능성이 있다",
            "next_action": "상품 조건 확인",
        },
        "checked_at": "2026-09-29T01:01:00+09:00",
        "checks": {
            key: {"passed": True, "evidence": "합성 테스트 판정; 실제 자료 검토 아님"}
            for key in (
                "answers_reader_question",
                "topic_specificity",
                "claims_sources_conditions",
                "benefits_conditions_risks",
                "standalone_comprehension",
                "dialogue_numbers_continuity",
            )
        },
        "claim_coverage": [
            {
                "fact_id": "identity",
                "panel": 1,
                "script_quote": "테스트용 투자 상품",
                "source_urls": ["https://example.org/fixture"],
                "assessment": "테스트용 일치",
            },
            {
                "fact_id": "risk",
                "panel": 2,
                "script_quote": "손실 가능성을 확인",
                "source_urls": ["https://example.org/fixture"],
                "assessment": "테스트용 일치",
            },
        ],
        "outcome": "pass",
    }


def modern_review_payload(root: Path) -> dict:
    return {
        "schema_version": "1.1",
        "episode_id": "EP-999",
        "writer_id": "test-writer",
        "reviewer_id": "test-reviewer",
        "content_sha256": semantic_content_sha256(
            root / "brief.json", root / "script.json"
        ),
        "layout_sha256": layout_sha256(root / "script.json"),
        "stages": ["blind_read", "card_source_checks"],
        "blind_read": {
            "completed_at": "2026-09-29T01:00:00+09:00",
            "topic_understood": "테스트 상품의 조건",
            "learned": "혜택과 손실 위험을 함께 확인해야 한다",
            "next_action": "공식 설명서를 확인한다",
            "reader_question_recalled": "어떤 상품이고 무엇을 확인해야 할까?",
            "action_steps": ["상품의 성격 확인", "손실 가능성 확인"],
            "repeated_panels": [],
            "awkward_phrases": [],
            "where_to_check_next": "최신 공식 상품설명서",
        },
        "checked_at": "2026-09-29T01:01:00+09:00",
        "checks": {
            key: {"passed": True, "evidence": "합성 테스트 판정; 실제 자료 검토 아님"}
            for key in (
                "answers_reader_question",
                "topic_specificity",
                "claims_sources_conditions",
                "benefits_conditions_risks",
                "standalone_comprehension",
                "dialogue_numbers_continuity",
                "promise_payoff_alignment",
                "distinct_panel_value",
                "ending_actionability",
                "scope_consistency",
                "korean_naturalness",
                "layout_density",
            )
        },
        "claim_coverage": [
            {
                "fact_id": "identity",
                "panel": 1,
                "script_quote": "테스트용 투자 상품",
                "source_urls": ["https://example.org/fixture"],
                "assessment": "테스트용 일치",
            },
            {
                "fact_id": "risk",
                "panel": 2,
                "script_quote": "손실 가능성을 확인",
                "source_urls": ["https://example.org/fixture"],
                "assessment": "테스트용 일치",
            },
        ],
        "outcome": "pass",
    }


def modernize_episode(root: Path) -> Path:
    brief_path = root / "brief.json"
    script_path = root / "script.json"
    brief = json.loads(brief_path.read_text(encoding="utf-8"))
    brief["schema_version"] = "1.3"
    brief["question_answer"]["reader_actions"] = [
        "상품의 성격을 확인한다",
        "손실 가능성을 확인한다",
    ]
    write_json(brief_path, brief)
    script = json.loads(script_path.read_text(encoding="utf-8"))
    script["schema_version"] = "1.2"
    for panel in script["panels"]:
        number = panel["panel"]
        panel.update(
            {
                "panel_job": f"독자 질문의 {number}번째 역할",
                "new_information": f"{number}번째 새 정보",
                "reader_takeaway": f"{number}번째 기억할 내용",
                "scope": "테스트 상품 일반",
                "text_budget": 72,
            }
        )
    write_json(script_path, script)
    write_json(root / "content-review.json", modern_review_payload(root))
    return root


def write_content_lock(root: Path) -> None:
    write_json(
        root / "content-lock.json",
        {
            "schema_version": "1.0",
            "episode_id": "EP-999",
            "content_sha256": semantic_content_sha256(
                root / "brief.json", root / "script.json"
            ),
            "mode": "user_accepted",
            "locked_at": "2026-09-29T01:02:00+09:00",
            "approval_note": "합성 테스트 승인",
        },
    )


def run_cli(episode: Path, name: str, *args: str) -> subprocess.CompletedProcess:
    result = subprocess.run(
        [sys.executable, str(SCRIPTS / name), "--episode-dir", str(episode), *args],
        capture_output=True,
        text=True,
        check=False,
    )
    (episode / f"{name}.stdout.txt").write_text(
        result.stdout or "(empty stdout)\n", encoding="utf-8"
    )
    (episode / f"{name}.stderr.txt").write_text(
        result.stderr or "(empty stderr)\n", encoding="utf-8"
    )
    return result


@pytest.mark.parametrize("layout", [(1, 1, 1, 1, 1), (1, 2, 4, 3, 2, 1)])
def test_no_humor_single_direction_and_requested_layout(
    tmp_path: Path, layout: tuple[int, ...]
) -> None:
    episode = informational_episode(tmp_path, layout)
    brief = BriefModel.model_validate_json((episode / "brief.json").read_text())
    assert len(brief.directions) == 1
    assert brief.selected_humor_engine_id is None
    assert brief.output_layout == layout
    assert recorded_issues(episode) == ()


@pytest.mark.parametrize("missing", ["reader_question", "sources", "checked_on"])
def test_missing_question_source_or_date_fails(tmp_path: Path, missing: str) -> None:
    episode = informational_episode(tmp_path)
    payload = json.loads((episode / "brief.json").read_text())
    card = payload["question_answer"]
    target = (
        card
        if missing == "reader_question"
        else card["required_facts"][0]
        if missing == "sources"
        else card["required_facts"][0]["sources"][0]
    )
    del target[missing]
    write_json(episode / "rejected-brief.json", payload)
    with pytest.raises(ValidationError) as error:
        BriefModel.model_validate(payload)
    (episode / "validation-error.txt").write_text(str(error.value), encoding="utf-8")


@pytest.mark.parametrize("file", ["brief.json", "script.json"])
def test_stale_approval_fails_after_input_change(tmp_path: Path, file: str) -> None:
    episode = informational_episode(tmp_path)
    path = episode / file
    path.write_text(path.read_text() + "\n", encoding="utf-8")
    assert any("stale" in issue for issue in recorded_issues(episode))


@pytest.mark.parametrize(
    "check",
    ["answers_reader_question", "topic_specificity", "benefits_conditions_risks"],
)
def test_reviewer_rejection_blocks_generic_or_missing_information(
    tmp_path: Path, check: str
) -> None:
    episode = informational_episode(tmp_path)
    payload = review_payload(episode)
    payload["checks"][check] = {
        "passed": False,
        "evidence": "상품 고유 정보 또는 위험 설명 누락",
    }
    payload["outcome"] = "fail"
    write_json(episode / "content-review.json", payload)
    assert recorded_issues(episode)
    payload["outcome"] = "pass"
    with pytest.raises(ValidationError):
        ContentReviewModel.model_validate(payload)


@pytest.mark.parametrize(
    "fault", ["coverage", "quote", "source", "writer", "order", "blind", "repeat"]
)
def test_incomplete_or_inconsistent_review_fails(tmp_path: Path, fault: str) -> None:
    episode = informational_episode(tmp_path)
    payload = review_payload(episode)
    if fault == "coverage":
        payload["claim_coverage"].pop()
    elif fault == "quote":
        payload["claim_coverage"][0]["script_quote"] = "대본에 없는 주장"
    elif fault == "source":
        payload["claim_coverage"][0]["source_urls"] = ["https://example.org/unknown"]
    elif fault == "writer":
        payload["reviewer_id"] = payload["writer_id"]
    elif fault == "order":
        payload["checked_at"] = payload["blind_read"]["completed_at"]
    elif fault == "blind":
        del payload["blind_read"]
    elif fault == "repeat":
        payload["review_round"] = 2
    write_json(episode / "content-review.json", payload)
    assert recorded_issues(episode)


def test_info_mock_compose_validate_and_history_round_trip(tmp_path: Path) -> None:
    episode = informational_episode(tmp_path / "episode")
    for name, args in [
        ("compose_episode.py", ("--mock",)),
        ("validate_episode.py", ()),
    ]:
        result = run_cli(episode, name, *args)
        assert result.returncode == 0, result.stderr
    history = tmp_path / "history.json"
    write_json(history, {"schema_version": "1.0", "episodes": []})
    result = run_cli(
        episode, "update_history.py", "--status", "draft", "--history", str(history)
    )
    assert result.returncode == 0, result.stderr
    entry = json.loads(history.read_text())["episodes"][0]
    assert entry["content_type"] == "informational"
    assert entry["humor_engine_id"] is None
    assert entry["status"] == "draft"


def test_missing_review_blocks_composition_validation_and_history(
    tmp_path: Path,
) -> None:
    episode = informational_episode(tmp_path / "episode")
    (episode / "content-review.json").unlink()
    history = tmp_path / "history.json"
    write_json(history, {"schema_version": "1.0", "episodes": []})
    before = history.read_bytes()
    for name, args in [
        ("compose_episode.py", ("--mock",)),
        ("validate_episode.py", ()),
        ("update_history.py", ("--status", "draft", "--history", str(history))),
    ]:
        result = run_cli(episode, name, *args)
        assert result.returncode != 0
        assert "content-review.json" in result.stderr
    assert not (episode / "raw").exists()
    assert history.read_bytes() == before


def test_passed_review_without_final_images_cannot_update_history(
    tmp_path: Path,
) -> None:
    episode = informational_episode(tmp_path / "episode")
    assert recorded_issues(episode) == ()
    history = tmp_path / "history.json"
    write_json(history, {"schema_version": "1.0", "episodes": []})
    before = history.read_bytes()
    result = run_cli(
        episode, "update_history.py", "--status", "draft", "--history", str(history)
    )
    assert result.returncode != 0
    assert "informational completion blocked" in result.stderr
    assert "final/page-01.png" in result.stderr
    assert history.read_bytes() == before
    assert not (episode / "final").exists()


def test_old_briefs_keep_three_direction_contract_without_new_review(
    tmp_path: Path,
) -> None:
    from test_story_quality_contract import _brief_payload

    for version in ("1.0", "1.1"):
        payload = _brief_payload(schema_version=version, topic_origin="user")
        assert BriefModel.model_validate(payload).schema_version == version
        write_json(tmp_path / "brief.json", payload)
        assert content_review_issues(tmp_path) == ()
        payload["directions"] = payload["directions"][:1]
        with pytest.raises(ValidationError):
            BriefModel.model_validate(payload)


def test_v13_requires_actions_panel_contract_and_expanded_review(
    tmp_path: Path,
) -> None:
    episode = modernize_episode(informational_episode(tmp_path))
    assert (
        BriefModel.model_validate_json(
            (episode / "brief.json").read_text()
        ).schema_version
        == "1.3"
    )
    assert (
        EpisodeScriptModel.model_validate_json(
            (episode / "script.json").read_text()
        ).schema_version
        == "1.2"
    )
    assert recorded_issues(episode) == ()

    brief = json.loads((episode / "brief.json").read_text())
    brief["question_answer"]["reader_actions"] = []
    with pytest.raises(ValidationError):
        BriefModel.model_validate(brief)

    script = json.loads((episode / "script.json").read_text())
    script["panels"][1]["panel_job"] = script["panels"][0]["panel_job"]
    with pytest.raises(ValidationError):
        EpisodeScriptModel.model_validate(script)

    review = modern_review_payload(episode)
    del review["checks"]["ending_actionability"]
    with pytest.raises(ValidationError):
        ContentReviewModel.model_validate(review)


def test_geometry_change_keeps_content_review_but_stales_layout_preflight(
    tmp_path: Path,
) -> None:
    episode = modernize_episode(informational_episode(tmp_path))
    write_content_lock(episode)
    preflight = run_cli(episode, "layout_preflight.py")
    assert preflight.returncode == 0, preflight.stderr
    assert content_review_issues(episode) == ()
    assert content_lock_issues(episode) == ()
    assert layout_preflight_issues(episode) == ()

    script_path = episode / "script.json"
    script = json.loads(script_path.read_text())
    script["panels"][0]["dialogue"][0]["x"] += 1
    write_json(script_path, script)

    assert content_review_issues(episode) == ()
    assert content_lock_issues(episode) == ()
    assert any("stale" in issue for issue in layout_preflight_issues(episode))


def test_dialogue_change_invalidates_review_and_lock(tmp_path: Path) -> None:
    episode = modernize_episode(informational_episode(tmp_path))
    write_content_lock(episode)
    script_path = episode / "script.json"
    script = json.loads(script_path.read_text())
    script["panels"][0]["dialogue"][0]["text"] = "바뀐 테스트용 투자 상품"
    write_json(script_path, script)

    assert any("semantic content" in issue for issue in content_review_issues(episode))
    assert any("stale" in issue for issue in content_lock_issues(episode))


def test_v13_composition_waits_for_lock_and_preflight(tmp_path: Path) -> None:
    episode = modernize_episode(informational_episode(tmp_path))
    blocked = run_cli(episode, "compose_episode.py", "--mock")
    assert blocked.returncode != 0
    assert "content lock" in blocked.stderr

    locked = run_cli(
        episode,
        "lock_content.py",
        "--mode",
        "user_accepted",
        "--approval-note",
        "합성 테스트 승인",
    )
    assert locked.returncode == 0, locked.stderr
    blocked = run_cli(episode, "compose_episode.py", "--mock")
    assert blocked.returncode != 0
    assert "layout preflight" in blocked.stderr

    preflight = run_cli(episode, "layout_preflight.py")
    assert preflight.returncode == 0, preflight.stderr
    composed = run_cli(episode, "compose_episode.py", "--mock")
    assert composed.returncode == 0, composed.stderr
