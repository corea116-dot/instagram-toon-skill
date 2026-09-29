from __future__ import annotations

import json
from datetime import datetime, timedelta
from pathlib import Path
from zoneinfo import ZoneInfo

import pytest
from pydantic import ValidationError
from typer.testing import CliRunner

from test_keyword_search import synthetic_evidence
from keyword_models import (
    InformationalKeywordEvidence,
    InformationalKeywordResearch,
    KeywordResearch,
    keyword_evidence_adapter,
    keyword_research_adapter,
)
from keyword_selection import select_topic
from topic_search import app


def informational_payload() -> dict:
    """Synthetic test data, never collected demand or official financial advice."""
    payload = synthetic_evidence().model_dump(mode="json")
    payload.update(schema_version="1.1", content_type="informational")
    keep = (
        "id", "topic", "keyword", "category", "keyword_type", "demand_reason",
        "source_relevance", "source_ids", "official_source_ids", "eligibility",
        "event_kind", "event_date",
    )
    payload["candidates"] = [
        {
            **{key: candidate[key] for key in keep},
            "reader_question": f"합성 상품 {candidate['id']}의 조건과 위험은 무엇인가?",
            "audience_fit": "합성 사회초년생 비교 질문",
            "safety_note": "합성 조건과 위험을 함께 확인; 가입 권유 아님",
            "duplicate_note": "합성 기존 키워드와 중복 없음",
            "gate_results": dict.fromkeys(
                ("audience_fit", "source_relevance", "safety", "duplicate"), True
            ),
        }
        for candidate in payload["candidates"]
    ]
    return payload


def test_no_humor_selects_with_identical_weighting_and_official_refs(tmp_path: Path) -> None:
    evidence = keyword_evidence_adapter.validate_python(informational_payload())
    decision = select_topic(evidence, "trending")
    assert decision.status == "selected"
    assert decision.selected_id == "0"
    assert decision.effective_type == "evergreen"
    assert [row.total for row in decision.scores] == [60, 55, 50, 45, 40]
    assert decision.evidence_label == "exact_monthly"
    research = InformationalKeywordResearch(evidence=evidence, decision=decision)
    artifact = tmp_path / "informational-research.json"
    artifact.write_text(research.model_dump_json(indent=2), encoding="utf-8")
    loaded = keyword_research_adapter.validate_json(artifact.read_bytes())
    assert loaded == research
    assert loaded.evidence.candidates[0].official_source_ids == ("official",)
    assert "scores" not in loaded.evidence.candidates[0].model_dump()
    assert "humor_engine_id" not in loaded.evidence.candidates[0].model_dump()


@pytest.mark.parametrize("gate", ["audience_fit", "source_relevance", "safety", "duplicate"])
def test_gate_rejects_rank_one_candidate(gate: str) -> None:
    payload = informational_payload()
    payload["candidates"][0]["gate_results"][gate] = False
    payload["candidates"][0]["eligibility"] = False
    decision = select_topic(InformationalKeywordEvidence.model_validate(payload), "evergreen")
    assert decision.selected_id == "1"
    assert decision.scores[0].rank == 1
    assert decision.scores[0].rejection_reason == "audience/source/safety/duplicate gate failed"


@pytest.mark.parametrize("source_id", ["missing", "naver"])
def test_missing_or_nonofficial_source_rejected(source_id: str) -> None:
    payload = informational_payload()
    payload["candidates"][0]["official_source_ids"] = [source_id]
    with pytest.raises(ValidationError, match="official facts need an official source"):
        InformationalKeywordEvidence.model_validate(payload)


def test_incomplete_platform_holds_with_null_metrics(tmp_path: Path) -> None:
    payload = informational_payload()
    payload["batches"][1]["values"].pop()
    evidence = InformationalKeywordEvidence.model_validate(payload)
    decision = select_topic(evidence, "evergreen")
    assert decision.status == "hold"
    assert all(row.google is None and row.total is None for row in decision.scores)
    (tmp_path / "incomplete-hold.json").write_text(
        InformationalKeywordResearch(evidence=evidence, decision=decision).model_dump_json(indent=2),
        encoding="utf-8",
    )


def test_official_event_fallback_and_monthly_priority() -> None:
    payload = informational_payload()
    payload["candidates"][0].update(
        keyword_type="trending", event_kind="deadline", event_date="2026-09-20"
    )
    relative = {**payload["batches"][0], "method": "relative_index"}
    relative["values"] = [
        {**item, "value": index * 20} for index, item in enumerate(relative["values"])
    ]
    payload["batches"].append(relative)
    result = select_topic(InformationalKeywordEvidence.model_validate(payload), "trending")
    assert result.selected_id == "0"
    assert result.effective_type == "trending"
    assert result.reason.startswith("official_event fallback")
    assert all(basis.method == "monthly_volume" for basis in result.bases)


def test_no_eligible_candidate_holds() -> None:
    payload = informational_payload()
    for candidate in payload["candidates"]:
        candidate["gate_results"]["safety"] = False
        candidate["eligibility"] = False
    result = select_topic(InformationalKeywordEvidence.model_validate(payload), "evergreen")
    assert result.status == "hold"
    assert result.selected_id is None


def test_tampered_decision_and_mixed_versions_rejected() -> None:
    evidence = InformationalKeywordEvidence.model_validate(informational_payload())
    payload = InformationalKeywordResearch(
        evidence=evidence, decision=select_topic(evidence, "evergreen")
    ).model_dump(mode="json")
    payload["decision"]["selected_id"] = "4"
    with pytest.raises(ValidationError, match="recomputed evidence ranking"):
        keyword_research_adapter.validate_python(payload)
    payload["schema_version"] = "1.2"
    with pytest.raises(ValidationError):
        keyword_research_adapter.validate_python(payload)


def test_legacy_evidence_and_research_remain_valid(tmp_path: Path) -> None:
    evidence = synthetic_evidence()
    research = KeywordResearch(evidence=evidence, decision=select_topic(evidence, "trending"))
    artifact = tmp_path / "legacy-research.json"
    artifact.write_text(research.model_dump_json(indent=2), encoding="utf-8")
    assert keyword_research_adapter.validate_json(artifact.read_bytes()) == research
    assert keyword_evidence_adapter.validate_json(evidence.model_dump_json()) == evidence


def test_schema_defaults_to_information_with_explicit_humor_option(tmp_path: Path) -> None:
    runner = CliRunner()
    for arguments, version in (([], "1.1"), (["--content-type", "humor"], "1.0")):
        output = tmp_path / f"evidence-{version}.schema.json"
        result = runner.invoke(app, ["schema", "--output", str(output), *arguments])
        assert result.exit_code == 0, result.output
        schema = json.loads(output.read_text(encoding="utf-8"))
        assert schema["properties"]["schema_version"]["const"] == version
        if version == "1.1":
            assert "content_type" in schema["required"]
            candidate = schema["$defs"]["InformationalKeywordCandidate"]
            assert "reader_question" in candidate["required"]
            assert "scores" not in candidate["properties"]


def test_info_cli_selected_and_hold_do_not_change_history(tmp_path: Path) -> None:
    payload = informational_payload()
    now = datetime.now(ZoneInfo("Asia/Seoul"))
    payload["researched_on"] = now.date().isoformat()
    for source in payload["sources"]:
        source["accessed_at"] = now.isoformat()
    for batch in payload["batches"]:
        batch["window_start"] = (now.date() - timedelta(days=43)).isoformat()
        batch["window_end"] = (now.date() - timedelta(days=13)).isoformat()
    history = tmp_path / "history.json"
    history.write_text('{"schema_version":"1.1","episodes":[]}', encoding="utf-8")
    original = history.read_bytes()
    for status, code in (("selected", 0), ("hold", 2)):
        evidence = tmp_path / f"{status}-evidence.json"
        if status == "hold":
            payload["batches"] = payload["batches"][:1]
        evidence.write_text(json.dumps(payload, ensure_ascii=False), encoding="utf-8")
        output = tmp_path / f"{status}-research.json"
        result = CliRunner().invoke(app, [
            "select", "--evidence", str(evidence), "--output", str(output),
            "--history", str(history),
        ])
        assert result.exit_code == code, result.output
        research = keyword_research_adapter.validate_json(output.read_bytes())
        assert research.schema_version == "1.3"
        assert research.content_type == "informational"
        assert research.decision.status == status
        assert history.read_bytes() == original


def test_info_research_completion_requires_current_content_and_visual_review(tmp_path: Path) -> None:
    from hashlib import sha256

    from keyword_history import completion_for_episode
    from test_informational_episode import informational_episode, review_payload, run_cli, write_json
    from topic_research_validation import topic_research_issues

    episode = informational_episode(tmp_path / "episode")
    evidence = InformationalKeywordEvidence.model_validate(informational_payload())
    research = InformationalKeywordResearch(evidence=evidence, decision=select_topic(evidence, "trending"))
    research_path = episode / "topic-research.json"
    research_path.write_text(research.model_dump_json(indent=2), encoding="utf-8")
    brief_path = episode / "brief.json"
    brief = json.loads(brief_path.read_text(encoding="utf-8"))
    brief.update(topic_origin="editorial_scout", topic=research.selected_topic)
    write_json(brief_path, brief)
    write_json(episode / "content-review.json", review_payload(episode))
    assert topic_research_issues(episode) == ()
    composed = run_cli(episode, "compose_episode.py", "--mock")
    assert composed.returncode == 0, composed.stderr
    state = {
        "status": "review_pending",
        "topic_research_sha256": sha256(research_path.read_bytes()).hexdigest(),
        "content_review": "PASS", "visual_qa": "PASS",
    }
    write_json(episode / "review-state.json", state)
    completion = completion_for_episode(episode, "editorial_scout")
    assert completion is not None
    assert completion.review_state == "review_pending"
    assert completion.requested_type == "trending"
    assert completion.effective_type == "evergreen"
    (episode / "completion.json").write_text(completion.model_dump_json(indent=2), encoding="utf-8")
    state["visual_qa"] = "FAIL"
    write_json(episode / "review-state.json", state)
    with pytest.raises(ValidationError):
        completion_for_episode(episode, "editorial_scout")
    state["visual_qa"] = "PASS"
    write_json(episode / "review-state.json", state)
    brief_path.write_text(brief_path.read_text(encoding="utf-8") + "\n", encoding="utf-8")
    with pytest.raises(ValueError, match="stale"):
        completion_for_episode(episode, "editorial_scout")


def test_info_research_cannot_use_humor_brief_but_old_research_allows_info_rewrite(tmp_path: Path) -> None:
    from test_informational_episode import informational_episode, write_json
    from test_story_quality_contract import _brief_payload
    from topic_research_validation import topic_research_issues

    episode = informational_episode(tmp_path / "episode")
    brief_path = episode / "brief.json"
    info_brief = json.loads(brief_path.read_text(encoding="utf-8"))
    info_evidence = InformationalKeywordEvidence.model_validate(informational_payload())
    info_research = InformationalKeywordResearch(
        evidence=info_evidence, decision=select_topic(info_evidence, "trending")
    )
    research_path = episode / "topic-research.json"
    research_path.write_text(info_research.model_dump_json(indent=2), encoding="utf-8")
    humor_brief = _brief_payload(schema_version="1.1", topic_origin="editorial_scout")
    humor_brief["topic"] = info_research.selected_topic
    write_json(brief_path, humor_brief)
    issues = topic_research_issues(episode)
    assert len(issues) == 1
    assert "informational topic research requires an informational brief" in issues[0]
    (episode / "rejected-mixed-mode.txt").write_text(issues[0] + "\n", encoding="utf-8")

    old_evidence = synthetic_evidence()
    old_research = KeywordResearch(
        evidence=old_evidence, decision=select_topic(old_evidence, "trending")
    )
    research_path.write_text(old_research.model_dump_json(indent=2), encoding="utf-8")
    info_brief.update(topic_origin="editorial_scout", topic=old_research.selected_topic)
    write_json(brief_path, info_brief)
    assert topic_research_issues(episode) == ()
