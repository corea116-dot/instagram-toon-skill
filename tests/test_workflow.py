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
# 1. Install uv (if not installed):
#      curl -LsSf https://astral.sh/uv/install.sh | sh
# 2. Run directly (no venv, no pip install needed):
#      uv run tests/test_workflow.py
# 3. Or make executable and run:
#      chmod +x tests/test_workflow.py && ./tests/test_workflow.py
# ──────────────────

from __future__ import annotations

import hashlib
import json
import os
from pathlib import Path
import subprocess
import sys

from PIL import Image
from pydantic import BaseModel, ConfigDict
import pytest


SKILL_ROOT = Path(__file__).resolve().parents[1]
SCRIPTS = SKILL_ROOT / "scripts"
EXPECTED_SIZE = (1080, 1350)
type JsonScalar = str | int | float | bool | None
type JsonValue = JsonScalar | list[JsonValue] | dict[str, JsonValue]


class BoxModel(BaseModel):
    model_config = ConfigDict(frozen=True)

    x: int
    y: int
    width: int
    height: int


class LayoutEntryModel(BaseModel):
    model_config = ConfigDict(frozen=True)

    panel: int
    bubble: int
    box: BoxModel
    safe_area: BoxModel
    font_size: int
    lines: tuple[str, ...]


class CompositionModel(BaseModel):
    model_config = ConfigDict(frozen=True)

    canvas: tuple[int, int]
    layouts: tuple[LayoutEntryModel, ...]


class HistoryEntryModel(BaseModel):
    model_config = ConfigDict(frozen=True)

    episode_id: str
    status: str


class HistoryModel(BaseModel):
    model_config = ConfigDict(frozen=True)

    schema_version: str
    episodes: tuple[HistoryEntryModel, ...]


def _write_json(path: Path, value: JsonValue) -> None:
    path.write_text(
        json.dumps(value, ensure_ascii=False, indent=2) + "\n", encoding="utf-8"
    )


def _make_episode(root: Path) -> Path:
    episode = root / "episodes" / "EP-001-새벽-세시"
    episode.mkdir(parents=True)
    brief: dict[str, JsonValue] = {
        "schema_version": "1.0",
        "episode_id": "EP-001",
        "title": "새벽 세 시의 결심",
        "topic": "일찍 자려다 휴대폰을 보며 새벽 3시까지 깨어 있는 직장인",
        "audience": "직장인",
        "tone": "가벼운 공감 유머",
        "characters": ["bgoon"],
        "directions": [
            {
                "id": "A",
                "premise": "일찍 자겠다는 결심과 자동 재생의 대결",
                "escalation": "한 영상이 끝날 때마다 다음 영상이 시작된다",
                "twist": "잠은 내일의 나에게 미룬다",
                "why_relatable": "직장인의 취침 전 휴대폰 습관",
            },
            {
                "id": "B",
                "premise": "한 영상만 보려다 밤을 샌다",
                "escalation": "취침 알림을 계속 미룬다",
                "twist": "알람이 취침 알림이 아니라 기상 알림이다",
                "why_relatable": "짧은 영상의 끝없는 추천",
            },
            {
                "id": "C",
                "premise": "휴대폰을 멀리 두려는 작은 작전",
                "escalation": "손이 닿지 않자 다른 기기를 찾는다",
                "twist": "스마트워치로 다시 확인한다",
                "why_relatable": "기기에서 벗어나기 어려운 일상",
            },
        ],
        "selected_direction": "A",
        "duplicate_check": {"matched_episode_ids": [], "result": "pass"},
        "sensitivity_check": {"issues": [], "result": "pass"},
    }
    beats = ("setup", "escalation", "tension", "twist")
    lines = (
        "오늘은 진짜 일찍 잔다",
        "일찍자려고누웠는데휴대폰을보다가새벽세시가되어버렸다",
        "딱 하나만 더 볼까?",
        "내일의 내가 자겠지",
    )
    panels: list[JsonValue] = []
    for number, (beat, line) in enumerate(zip(beats, lines, strict=True), start=1):
        panels.append(
            {
                "panel": number,
                "beat": beat,
                "scene": f"침실에서 이어지는 장면 {number}",
                "expression": "피곤하지만 휴대폰에 집중한 표정",
                "action": "침대에 누워 휴대폰을 본다",
                "props": ["휴대폰", "베개", "이불"],
                "background": "늦은 밤의 침실",
                "camera": "미디엄 숏",
                "dialogue": [
                    {
                        "speaker": "bgoon",
                        "text": line,
                        "x": 70,
                        "y": 65 if number != 4 else 1010,
                        "width": 940,
                        "height": 260,
                    }
                ],
            }
        )
    script: dict[str, JsonValue] = {
        "schema_version": "1.0",
        "episode_id": "EP-001",
        "title": "새벽 세 시의 결심",
        "panels": panels,
    }
    _write_json(episode / "brief.json", brief)
    _write_json(episode / "script.json", script)
    (episode / "caption.txt").write_text(
        "일찍 자려던 사람, 저뿐인가요?\n", encoding="utf-8"
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


def test_full_mock_episode_is_deterministic_when_composed(tmp_path: Path) -> None:
    episode = _make_episode(tmp_path)

    first = _run("compose_episode.py", "--episode-dir", str(episode), "--mock")
    assert first.returncode == 0, first.stderr
    expected = [episode / "final" / "four-panel.png"] + [
        episode / "final" / f"carousel-{number}.png" for number in range(1, 5)
    ]
    first_hashes = tuple(_digest(path) for path in expected)

    second = _run("compose_episode.py", "--episode-dir", str(episode), "--mock")
    assert second.returncode == 0, second.stderr
    assert tuple(_digest(path) for path in expected) == first_hashes
    for path in expected:
        with Image.open(path) as image:
            assert image.size == EXPECTED_SIZE
            assert image.format == "PNG"

    validated = _run("validate_episode.py", "--episode-dir", str(episode))
    assert validated.returncode == 0, validated.stderr
    assert (episode / "qa-report.md").is_file()


def test_only_requested_panel_changes_when_regenerated(tmp_path: Path) -> None:
    episode = _make_episode(tmp_path)
    initial = _run("compose_episode.py", "--episode-dir", str(episode), "--mock")
    assert initial.returncode == 0, initial.stderr
    raw_paths = [episode / "raw" / f"panel-{number}.png" for number in range(1, 5)]
    carousel_paths = [
        episode / "final" / f"carousel-{number}.png" for number in range(1, 5)
    ]
    raw_before = tuple(_digest(path) for path in raw_paths)
    carousel_before = tuple(_digest(path) for path in carousel_paths)
    grid_before = _digest(episode / "final" / "four-panel.png")

    regenerated = _run(
        "compose_episode.py",
        "--episode-dir",
        str(episode),
        "--mock",
        "--panel",
        "3",
    )
    assert regenerated.returncode == 0, regenerated.stderr
    raw_after = tuple(_digest(path) for path in raw_paths)
    carousel_after = tuple(_digest(path) for path in carousel_paths)

    assert raw_after[2] != raw_before[2]
    assert carousel_after[2] != carousel_before[2]
    assert raw_after[:2] + raw_after[3:] == raw_before[:2] + raw_before[3:]
    assert (
        carousel_after[:2] + carousel_after[3:]
        == carousel_before[:2] + carousel_before[3:]
    )
    assert _digest(episode / "final" / "four-panel.png") != grid_before


def test_korean_text_wraps_inside_safe_area_when_composed(tmp_path: Path) -> None:
    episode = _make_episode(tmp_path)
    result = _run("compose_episode.py", "--episode-dir", str(episode), "--mock")
    assert result.returncode == 0, result.stderr

    manifest = CompositionModel.model_validate_json(
        (episode / "final" / "composition.json").read_text(encoding="utf-8")
    )
    assert manifest.canvas == EXPECTED_SIZE
    assert len(manifest.layouts) == 4
    assert len(manifest.layouts[1].lines) >= 2
    for layout in manifest.layouts:
        box = layout.box
        safe = layout.safe_area
        assert 0 <= box.x and box.x + box.width <= EXPECTED_SIZE[0]
        assert 0 <= box.y and box.y + box.height <= EXPECTED_SIZE[1]
        assert safe.x <= box.x and box.x + box.width <= safe.x + safe.width
        assert safe.y <= box.y and box.y + box.height <= safe.y + safe.height
        assert layout.font_size >= 26


def test_history_update_is_idempotent_when_repeated(tmp_path: Path) -> None:
    episode = _make_episode(tmp_path)
    history_path = tmp_path / "episode-history.json"
    history_path.write_text(
        '{"schema_version":"1.0","episodes":[]}\n', encoding="utf-8"
    )

    for _ in range(2):
        result = _run(
            "update_history.py",
            "--episode-dir",
            str(episode),
            "--history",
            str(history_path),
            "--status",
            "draft",
        )
        assert result.returncode == 0, result.stderr

    history = HistoryModel.model_validate_json(history_path.read_text(encoding="utf-8"))
    assert len(history.episodes) == 1
    assert history.episodes[0].episode_id == "EP-001"
    assert history.episodes[0].status == "draft"


def test_invalid_script_returns_a_clear_cli_failure(tmp_path: Path) -> None:
    episode = _make_episode(tmp_path)
    raw = json.loads((episode / "script.json").read_text(encoding="utf-8"))
    raw["panels"] = raw["panels"][:3]
    (episode / "script.json").write_text(
        json.dumps(raw, ensure_ascii=False), encoding="utf-8"
    )

    result = _run("compose_episode.py", "--episode-dir", str(episode), "--mock")

    assert result.returncode != 0
    assert "script.json" in result.stderr


if __name__ == "__main__":
    raise SystemExit(pytest.main([__file__, "-q"]))
