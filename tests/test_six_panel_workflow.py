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
#      uv run tests/test_six_panel_workflow.py
# 3. Or make executable and run:
#      chmod +x tests/test_six_panel_workflow.py && ./tests/test_six_panel_workflow.py
# ──────────────────

from __future__ import annotations

import hashlib
import json
import os
from pathlib import Path
import subprocess
import importlib
import sys
from typing import ClassVar, Literal

from PIL import Image
from pydantic import BaseModel, ConfigDict
import pytest


SKILL_ROOT = Path(__file__).resolve().parents[1]
SCRIPTS = SKILL_ROOT / "scripts"
EXPECTED_SIZE = (1080, 1350)
type JsonScalar = str | int | float | bool | None
type JsonValue = JsonScalar | list[JsonValue] | dict[str, JsonValue]
type OpeningBeat = Literal["opening_hook", "development_setup"]

sys.path.insert(0, str(SCRIPTS))
compose_episode = importlib.import_module("compose_episode")


class HistoryEntryModel(BaseModel):
    model_config: ClassVar[ConfigDict] = ConfigDict(frozen=True)

    twist: str


class HistoryModel(BaseModel):
    model_config: ClassVar[ConfigDict] = ConfigDict(frozen=True)

    episodes: tuple[HistoryEntryModel, ...]


def _write_json(path: Path, value: JsonValue) -> None:
    _ = path.write_text(
        json.dumps(value, ensure_ascii=False, indent=2) + "\n", encoding="utf-8"
    )


def _make_episode(root: Path, opening_beat: OpeningBeat = "opening_hook") -> Path:
    episode = root / "episodes" / "EP-002-월요일-알람"
    episode.mkdir(parents=True)
    brief: dict[str, JsonValue] = {
        "schema_version": "1.0",
        "episode_id": "EP-002",
        "title": "월요일 알람",
        "topic": "알람을 끄고 5분만 더 자려는 직장인",
        "audience": "직장인",
        "tone": "가벼운 공감 유머",
        "characters": ["bgoon"],
        "directions": [
            {
                "id": direction,
                "premise": f"알람과 협상하는 아침 {direction}",
                "escalation": "5분이 계속 늘어난다",
                "twist": "알람이 아니라 회사 전화가 울린다",
                "why_relatable": "출근 전 누구나 해 본 미루기",
            }
            for direction in ("A", "B", "C")
        ],
        "selected_direction": "A",
        "duplicate_check": {"matched_episode_ids": [], "result": "pass"},
        "sensitivity_check": {"issues": [], "result": "pass"},
        "status": "draft",
    }
    sections = (
        "opening",
        "development",
        "development",
        "development",
        "development",
        "ending",
    )
    beats = (
        opening_beat,
        "development_setup",
        "development_escalation",
        "development_complication",
        "development_turn",
        "ending_payoff",
    )
    lines = (
        "지금 일어나면 기적이다",
        "5분만",
        "진짜 5분만",
        "이번엔 눈만 감을게",
        "왜 이렇게 조용하지?",
        "팀장님 전화다",
    )
    panels: list[JsonValue] = []
    for number, (section, beat, line) in enumerate(
        zip(sections, beats, lines, strict=True), start=1
    ):
        panels.append(
            {
                "panel": number,
                "section": section,
                "beat": beat,
                "scene": f"침실에서 이어지는 아침 장면 {number}",
                "expression": "긴장과 졸음이 섞인 표정",
                "action": "알람을 확인하고 이불을 당긴다",
                "props": ["휴대폰", "이불"],
                "background": "단순한 침실",
                "camera": "후킹되는 근접 구도" if number == 1 else "미디엄 숏",
                "dialogue": [
                    {
                        "speaker": "bgoon",
                        "text": line,
                        "x": 70,
                        "y": 65 if number < 6 else 1010,
                        "width": 940,
                        "height": 260,
                    }
                ],
            }
        )
    script: dict[str, JsonValue] = {
        "schema_version": "1.0",
        "episode_id": "EP-002",
        "title": "월요일 알람",
        "panels": panels,
    }
    _write_json(episode / "brief.json", brief)
    _write_json(episode / "script.json", script)
    _ = (episode / "caption.txt").write_text(
        "5분만 더가 제일 위험한 말이죠.\n", encoding="utf-8"
    )
    return episode


def _run(script: str, *arguments: str) -> subprocess.CompletedProcess[str]:
    environment = os.environ | {"PYTHONDONTWRITEBYTECODE": "1"}
    return subprocess.run(
        [sys.executable, str(SCRIPTS / script), *arguments],
        check=False,
        capture_output=True,
        text=True,
        env=environment,
    )


def _digest(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def _primary_references() -> list[str]:
    visual_style = json.loads(
        (SKILL_ROOT / "memory" / "visual-style.json").read_text(encoding="utf-8")
    )
    return visual_style["reference_policy"]["primary_reference_images"]


def test_six_panel_story_exports_three_delivery_images_when_composed(
    tmp_path: Path,
) -> None:
    episode = _make_episode(tmp_path)
    references = _primary_references()
    assert len(references) == 3
    assert all((SKILL_ROOT / reference).is_file() for reference in references)

    composed = _run("compose_episode.py", "--episode-dir", str(episode), "--mock")
    assert composed.returncode == 0, composed.stderr
    for number in range(1, 7):
        prompt = json.loads(
            (episode / "prompts" / f"panel-{number}.json").read_text(encoding="utf-8")
        )
        assert prompt["reference_images"][:3] == references
    expected = (
        episode / "final" / "opening.png",
        episode / "final" / "development-four-panel.png",
        episode / "final" / "ending.png",
    )
    for path in expected:
        with Image.open(path) as image:
            assert image.size == EXPECTED_SIZE
            assert image.format == "PNG"
    exported_names = tuple(sorted(path.name for path in (episode / "final").glob("*.png")))
    assert exported_names == (
        "development-four-panel.png",
        "ending.png",
        "opening.png",
    )

    validated = _run("validate_episode.py", "--episode-dir", str(episode))
    assert validated.returncode == 0, validated.stderr
    assert not tuple(episode.rglob("*.tmp"))


def test_six_panel_delivery_keeps_composed_panel_assets_out_of_final(
    tmp_path: Path,
) -> None:
    episode = _make_episode(tmp_path)
    composed = _run("compose_episode.py", "--episode-dir", str(episode), "--mock")
    assert composed.returncode == 0, composed.stderr

    composed_names = tuple(
        sorted(path.name for path in (episode / "composed").glob("*.png"))
    )
    assert composed_names == tuple(f"panel-{number}.png" for number in range(1, 7))


def test_only_fifth_panel_and_development_composite_change_when_regenerated(
    tmp_path: Path,
) -> None:
    episode = _make_episode(tmp_path)
    references = _primary_references()
    initial = _run("compose_episode.py", "--episode-dir", str(episode), "--mock")
    assert initial.returncode == 0, initial.stderr
    raw_paths = tuple(episode / "raw" / f"panel-{number}.png" for number in range(1, 7))
    before = tuple(_digest(path) for path in raw_paths)
    before_final = tuple(
        _digest(episode / "final" / name)
        for name in ("opening.png", "development-four-panel.png", "ending.png")
    )

    regenerated = _run(
        "compose_episode.py", "--episode-dir", str(episode), "--mock", "--panel", "5"
    )
    assert regenerated.returncode == 0, regenerated.stderr
    after = tuple(_digest(path) for path in raw_paths)
    assert after[4] != before[4]
    assert after[:4] + after[5:] == before[:4] + before[5:]
    after_final = tuple(
        _digest(episode / "final" / name)
        for name in ("opening.png", "development-four-panel.png", "ending.png")
    )
    assert after_final[1] != before_final[1]
    assert after_final[0] == before_final[0]
    assert after_final[2] == before_final[2]
    prompt = json.loads(
        (episode / "prompts" / "panel-5.json").read_text(encoding="utf-8")
    )
    assert prompt["reference_images"][:3] == references


def test_hard_banned_phrase_blocks_validation(tmp_path: Path) -> None:
    episode = _make_episode(tmp_path)
    composed = _run("compose_episode.py", "--episode-dir", str(episode), "--mock")
    assert composed.returncode == 0, composed.stderr
    _ = (episode / "caption.txt").write_text("자해를 권한다", encoding="utf-8")

    validated = _run("validate_episode.py", "--episode-dir", str(episode))

    assert validated.returncode == 1
    assert "hard_banned self-harm-encouragement" in validated.stderr


def test_review_required_phrase_is_advisory_in_qa_report(tmp_path: Path) -> None:
    episode = _make_episode(tmp_path)
    composed = _run("compose_episode.py", "--episode-dir", str(episode), "--mock")
    assert composed.returncode == 0, composed.stderr
    _ = (episode / "caption.txt").write_text("팀장님의 보복 인사가 걱정된다", encoding="utf-8")

    validated = _run("validate_episode.py", "--episode-dir", str(episode))

    assert validated.returncode == 0, validated.stderr
    report = (episode / "qa-report.md").read_text(encoding="utf-8")
    assert "Automated validation: **PASS**" in report
    assert "review_required workplace-power" in report


def test_regular_workplace_phrase_does_not_require_review(tmp_path: Path) -> None:
    episode = _make_episode(tmp_path)
    composed = _run("compose_episode.py", "--episode-dir", str(episode), "--mock")
    assert composed.returncode == 0, composed.stderr
    _ = (episode / "caption.txt").write_text("회의가 길어져 퇴근이 늦었다", encoding="utf-8")

    validated = _run("validate_episode.py", "--episode-dir", str(episode))

    assert validated.returncode == 0, validated.stderr
    report = (episode / "qa-report.md").read_text(encoding="utf-8")
    assert "review_required workplace-power" not in report


def test_native_partial_compose_refreshes_manifest_and_reuses_raw_panel(
    tmp_path: Path,
) -> None:
    episode = _make_episode(tmp_path)
    references = _primary_references()
    composed = _run("compose_episode.py", "--episode-dir", str(episode), "--mock")
    assert composed.returncode == 0, composed.stderr
    prompt_path = episode / "prompts" / "panel-4.json"
    prompt = json.loads(prompt_path.read_text(encoding="utf-8"))
    prompt["reference_images"] = ["legacy-extra.png", *prompt["reference_images"]]
    _write_json(prompt_path, prompt)
    raw_path = episode / "raw" / "panel-4.png"
    raw_before = _digest(raw_path)

    composed = _run("compose_episode.py", "--episode-dir", str(episode), "--panel", "4")

    assert composed.returncode == 0, composed.stderr
    refreshed = json.loads(prompt_path.read_text(encoding="utf-8"))
    assert refreshed["revision"] == 1
    assert refreshed["mode"] == "native"
    assert refreshed["reference_images"] == [*references, "legacy-extra.png"]
    assert _digest(raw_path) == raw_before


@pytest.mark.parametrize(
    ("references", "error_match"),
    (
        (
            [
                "assets/references/styles/missing-primary-reference.png",
                "assets/references/styles/screenshots-2026-07-19/스크린샷 2026-07-19 오후 4.07.58.png",
                "assets/references/styles/screenshots-2026-07-19/스크린샷 2026-07-19 오후 4.08.23.png",
            ],
            "missing-primary-reference",
        ),
        (
            [
                "/tmp/primary-reference.png",
                "assets/references/styles/screenshots-2026-07-19/스크린샷 2026-07-19 오후 4.07.58.png",
                "assets/references/styles/screenshots-2026-07-19/스크린샷 2026-07-19 오후 4.08.23.png",
            ],
            "relative",
        ),
        (
            [
                "../visual-style.json",
                "assets/references/styles/screenshots-2026-07-19/스크린샷 2026-07-19 오후 4.07.58.png",
                "assets/references/styles/screenshots-2026-07-19/스크린샷 2026-07-19 오후 4.08.23.png",
            ],
            "path traversal",
        ),
        (
            [
                "assets/references/styles/screenshots-2026-07-19/../screenshots-2026-07-19/스크린샷 2026-07-19 오후 4.07.58.png",
                "assets/references/styles/screenshots-2026-07-19/스크린샷 2026-07-19 오후 4.07.58.png",
                "assets/references/styles/screenshots-2026-07-19/스크린샷 2026-07-19 오후 4.08.23.png",
            ],
            "must not contain path traversal",
        ),
        (
            [
                "assets/references/styles",
                "assets/references/styles/screenshots-2026-07-19/스크린샷 2026-07-19 오후 4.07.58.png",
                "assets/references/styles/screenshots-2026-07-19/스크린샷 2026-07-19 오후 4.08.23.png",
            ],
            "not a regular file",
        ),
        (
            ["assets/references/styles/screenshots-2026-07-19/스크린샷 2026-07-19 오후 4.07.38.png"],
            "three paths",
        ),
    ),
)
def test_compose_fails_before_creating_prompts_for_invalid_primary_references(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
    references: list[str],
    error_match: str,
) -> None:
    episode = _make_episode(tmp_path)
    visual_style = json.loads(
        (SKILL_ROOT / "memory" / "visual-style.json").read_text(encoding="utf-8")
    )
    visual_style["reference_policy"]["primary_reference_images"] = references
    invalid_style = tmp_path / "visual-style.json"
    _write_json(invalid_style, visual_style)
    monkeypatch.setattr(compose_episode, "VISUAL_STYLE_PATH", invalid_style)

    with pytest.raises(compose_episode.RenderError, match=error_match):
        compose_episode.compose(
            compose_episode.ComposeOptions(episode_dir=episode, mock=True, panel=None)
        )

    assert not (episode / "prompts").exists()


def test_compose_rejects_primary_reference_symlink_escape(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    episode = _make_episode(tmp_path)
    skill_root = tmp_path / "skill"
    outside_file = tmp_path / "outside.png"
    outside_file.write_bytes(b"not a real image")
    escaped_reference = skill_root / "references" / "escaped.png"
    escaped_reference.parent.mkdir(parents=True)
    escaped_reference.symlink_to(outside_file)

    visual_style = json.loads(
        (SKILL_ROOT / "memory" / "visual-style.json").read_text(encoding="utf-8")
    )
    visual_style["reference_policy"]["primary_reference_images"] = [
        "references/escaped.png",
        "references/escaped.png",
        "references/escaped.png",
    ]
    invalid_style = tmp_path / "visual-style.json"
    _write_json(invalid_style, visual_style)
    monkeypatch.setattr(compose_episode, "SKILL_ROOT", skill_root)
    monkeypatch.setattr(compose_episode, "VISUAL_STYLE_PATH", invalid_style)

    with pytest.raises(compose_episode.RenderError, match="escapes"):
        compose_episode.compose(
            compose_episode.ComposeOptions(episode_dir=episode, mock=True, panel=None)
        )

    assert not (episode / "prompts").exists()


def test_six_panel_script_fails_when_opening_hook_is_missing(tmp_path: Path) -> None:
    episode = _make_episode(tmp_path, opening_beat="development_setup")

    result = _run("compose_episode.py", "--episode-dir", str(episode), "--mock")

    assert result.returncode != 0
    assert "script.json" in result.stderr


def test_history_uses_sixth_panel_as_ending_when_updated(tmp_path: Path) -> None:
    episode = _make_episode(tmp_path)
    history = tmp_path / "episode-history.json"
    _ = history.write_text('{"schema_version":"1.0","episodes":[]}\n', encoding="utf-8")

    result = _run(
        "update_history.py",
        "--episode-dir",
        str(episode),
        "--history",
        str(history),
        "--status",
        "draft",
    )

    assert result.returncode == 0, result.stderr
    payload = HistoryModel.model_validate_json(history.read_text(encoding="utf-8"))
    assert payload.episodes[0].twist == "팀장님 전화다"


if __name__ == "__main__":
    raise SystemExit(pytest.main([__file__, "-q"]))
