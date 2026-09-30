from __future__ import annotations

import json
import sys
from datetime import datetime, timedelta
from hashlib import sha256
from pathlib import Path
from zoneinfo import ZoneInfo

import pytest
from typer.testing import CliRunner

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "scripts"))

from episode_models import BriefModel
from keyword_history import next_keyword_type
from keyword_models import KeywordEvidence, KeywordResearch
from keyword_selection import select_topic
from test_keyword_search import synthetic_evidence
from test_topic_discovery_contract import (
    _make_episode,
    _run,
    _upgrade_editorial_episode_to_v11,
    _write_topic_research,
)
from topic_search import app


def _research(episode: Path) -> Path:
    evidence = synthetic_evidence()
    (episode / "keyword-evidence.json").write_text(
        evidence.model_dump_json(indent=2), encoding="utf-8"
    )
    research = KeywordResearch(
        evidence=evidence, decision=select_topic(evidence, "trending")
    )
    path = episode / "topic-research.json"
    path.write_text(research.model_dump_json(indent=2), encoding="utf-8")
    brief_path = episode / "brief.json"
    brief = BriefModel.model_validate_json(brief_path.read_bytes())
    updated = brief.model_copy(update={"topic": research.selected_topic})
    brief_path.write_text(updated.model_dump_json(indent=2), encoding="utf-8")
    return path


def _episode(root: Path) -> Path:
    episode = _make_episode(root, "editorial_scout")
    _write_topic_research(episode)
    _upgrade_editorial_episode_to_v11(episode)
    _research(episode)
    return episode


def test_search_only_cli_and_hold_leave_history_unchanged(tmp_path: Path) -> None:
    history = tmp_path / "history.json"
    history.write_text('{"schema_version":"1.1","episodes":[]}', encoding="utf-8")
    before = history.read_bytes()
    evidence = tmp_path / "keyword-evidence.json"
    now = datetime.now(ZoneInfo("Asia/Seoul"))
    payload = synthetic_evidence().model_dump(mode="json")
    payload["researched_on"] = now.date().isoformat()
    for source in payload["sources"]:
        source["accessed_at"] = now.isoformat()
    for batch in payload["batches"]:
        batch["window_start"] = (now.date() - timedelta(days=43)).isoformat()
        batch["window_end"] = (now.date() - timedelta(days=13)).isoformat()
    collected = KeywordEvidence.model_validate(payload)
    evidence.write_text(collected.model_dump_json(), encoding="utf-8")
    runner = CliRunner()
    result = runner.invoke(
        app,
        [
            "select",
            "--evidence",
            str(evidence),
            "--output",
            str(tmp_path / "selected.json"),
            "--history",
            str(history),
        ],
    )
    assert result.exit_code == 0, result.output
    assert '"status": "selected"' in result.output
    held = collected.model_copy(update={"batches": ()})
    evidence.write_text(held.model_dump_json(), encoding="utf-8")
    result = runner.invoke(
        app,
        [
            "select",
            "--evidence",
            str(evidence),
            "--output",
            str(tmp_path / "held.json"),
            "--history",
            str(history),
        ],
    )
    assert result.exit_code == 2, result.output
    assert history.read_bytes() == before


def test_cli_rejects_malformed_evidence_without_output(tmp_path: Path) -> None:
    evidence = tmp_path / "bad.json"
    evidence.write_text('{"schema_version":"1.0"}', encoding="utf-8")
    output = tmp_path / "research.json"
    result = CliRunner().invoke(
        app, ["select", "--evidence", str(evidence), "--output", str(output)]
    )
    assert result.exit_code == 1
    assert not output.exists()


def test_generated_episode_advances_once_at_review_pending(tmp_path: Path) -> None:
    episode = _episode(tmp_path)
    history = tmp_path / "history.json"
    history.write_text('{"schema_version":"1.1","episodes":[]}', encoding="utf-8")
    arguments = (
        "--episode-dir",
        str(episode),
        "--history",
        str(history),
        "--status",
        "draft",
    )
    blocked = _run("update_history.py", *arguments)
    assert blocked.returncode == 1
    assert next_keyword_type(history) == "trending"
    composed = _run("compose_episode.py", "--episode-dir", str(episode), "--mock")
    assert composed.returncode == 0, composed.stderr
    review = {
        "status": "review_pending",
        "topic_research_sha256": sha256(
            (episode / "topic-research.json").read_bytes()
        ).hexdigest(),
        "story_qa": "PASS",
        "dialogue_qa": "PASS",
        "continuity_qa": "PASS",
        "visual_qa": "PASS",
    }
    (episode / "review-state.json").write_text(json.dumps(review), encoding="utf-8")
    updated = _run("update_history.py", *arguments)
    assert updated.returncode == 0, updated.stderr
    assert next_keyword_type(history) == "evergreen"
    retry = _run("update_history.py", *arguments)
    assert retry.returncode == 0, retry.stderr
    assert next_keyword_type(history) == "evergreen"
    (episode / "raw" / "panel-1.png").unlink()
    invalid = _run("update_history.py", *arguments)
    assert invalid.returncode == 1
    assert next_keyword_type(history) == "evergreen"


def test_new_research_is_accepted_by_existing_validator(tmp_path: Path) -> None:
    episode = _episode(tmp_path)
    composed = _run("compose_episode.py", "--episode-dir", str(episode), "--mock")
    assert composed.returncode == 0, composed.stderr
    result = _run("validate_episode.py", "--episode-dir", str(episode))
    assert result.returncode == 0, result.stderr


def test_growth_windows_must_be_comparable() -> None:
    data = synthetic_evidence().model_dump(mode="json")
    data["batches"][0]["values"][0]["previous_value"] = 10
    with pytest.raises(ValueError, match="earlier comparison window"):
        KeywordEvidence.model_validate(data)
