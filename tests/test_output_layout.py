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

from __future__ import annotations

import hashlib
import json
import os
from pathlib import Path
import subprocess
import sys
from typing import Literal

from PIL import Image
import pytest


SKILL_ROOT = Path(__file__).resolve().parents[1]
SCRIPTS = SKILL_ROOT / "scripts"
EXPECTED_SIZE = (1080, 1350)


def _write_json(path: Path, value: dict[str, object]) -> None:
    _ = path.write_text(
        json.dumps(value, ensure_ascii=False, indent=2) + "\n", encoding="utf-8"
    )


def _make_episode(root: Path, output_layout: tuple[int, ...]) -> Path:
    episode = root / "episodes" / "EP-003-layout"
    episode.mkdir(parents=True)
    panel_count = sum(output_layout)
    panels: list[dict[str, object]] = []
    for number in range(1, panel_count + 1):
        section: Literal["opening", "development", "ending"]
        beat: Literal["opening_hook", "development", "ending_payoff"]
        if number == 1:
            section, beat = "opening", "opening_hook"
        elif number == panel_count:
            section, beat = "ending", "ending_payoff"
        else:
            section, beat = "development", "development"
        panels.append(
            {
                "panel": number,
                "section": section,
                "beat": beat,
                "scene": f"이어지는 장면 {number}",
                "expression": "집중한 표정",
                "action": "휴대폰을 확인한다",
                "props": ["휴대폰"],
                "background": "단순한 방",
                "camera": "미디엄 숏",
                "dialogue": [
                    {
                        "speaker": "bgoon",
                        "text": f"패널 {number}",
                        "x": 70,
                        "y": 65,
                        "width": 940,
                        "height": 260,
                    }
                ],
            }
        )
    _write_json(
        episode / "brief.json",
        {
            "schema_version": "1.0",
            "episode_id": "EP-003",
            "title": "가변 출력",
            "topic": "출력 조합",
            "audience": "독자",
            "tone": "가벼운 유머",
            "characters": ["bgoon"],
            "directions": [
                {
                    "id": direction,
                    "premise": "짧은 전제",
                    "escalation": "상태 변화",
                    "twist": "짧은 반전",
                    "why_relatable": "공감",
                }
                for direction in ("A", "B", "C")
            ],
            "selected_direction": "A",
            "duplicate_check": {"matched_episode_ids": [], "result": "pass"},
            "sensitivity_check": {"issues": [], "result": "pass"},
            "status": "draft",
        },
    )
    _write_json(
        episode / "script.json",
        {
            "schema_version": "1.1",
            "episode_id": "EP-003",
            "title": "가변 출력",
            "output_layout": list(output_layout),
            "panels": panels,
        },
    )
    _ = (episode / "caption.txt").write_text("가변 출력 테스트\n", encoding="utf-8")
    return episode


def _run(script: str, *arguments: str) -> subprocess.CompletedProcess[str]:
    return subprocess.run(
        [sys.executable, str(SCRIPTS / script), *arguments],
        check=False,
        capture_output=True,
        text=True,
        env=os.environ | {"PYTHONDONTWRITEBYTECODE": "1"},
    )


def _digest(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


@pytest.mark.parametrize(
    "output_layout",
    ((1, 1, 1, 1, 1), (2, 3), (3, 2), (4, 1)),
)
def test_layout_exports_sequential_pages_at_postable_size(
    tmp_path: Path, output_layout: tuple[int, ...]
) -> None:
    episode = _make_episode(tmp_path, output_layout)

    composed = _run("compose_episode.py", "--episode-dir", str(episode), "--mock")

    assert composed.returncode == 0, composed.stderr
    expected_names = tuple(
        f"page-{number:02}.png" for number in range(1, len(output_layout) + 1)
    )
    assert tuple(sorted(path.name for path in (episode / "final").glob("*.png"))) == expected_names
    for name in expected_names:
        with Image.open(episode / "final" / name) as image:
            assert image.size == EXPECTED_SIZE
            assert image.format == "PNG"
    validated = _run("validate_episode.py", "--episode-dir", str(episode))
    assert validated.returncode == 0, validated.stderr


def test_partial_regeneration_changes_only_the_page_containing_the_panel(
    tmp_path: Path,
) -> None:
    episode = _make_episode(tmp_path, (2, 3))
    initial = _run("compose_episode.py", "--episode-dir", str(episode), "--mock")
    assert initial.returncode == 0, initial.stderr
    raw_before = tuple(
        _digest(episode / "raw" / f"panel-{number}.png") for number in range(1, 6)
    )
    page_before = tuple(
        _digest(episode / "final" / f"page-{number:02}.png") for number in range(1, 3)
    )

    regenerated = _run(
        "compose_episode.py", "--episode-dir", str(episode), "--mock", "--panel", "3"
    )

    assert regenerated.returncode == 0, regenerated.stderr
    raw_after = tuple(
        _digest(episode / "raw" / f"panel-{number}.png") for number in range(1, 6)
    )
    page_after = tuple(
        _digest(episode / "final" / f"page-{number:02}.png") for number in range(1, 3)
    )
    assert raw_after[2] != raw_before[2]
    assert raw_after[:2] + raw_after[3:] == raw_before[:2] + raw_before[3:]
    assert page_after[0] == page_before[0]
    assert page_after[1] != page_before[1]


def test_full_compose_removes_pages_not_in_the_current_layout(tmp_path: Path) -> None:
    episode = _make_episode(tmp_path, (1, 1, 1, 1, 1))
    initial = _run("compose_episode.py", "--episode-dir", str(episode), "--mock")
    assert initial.returncode == 0, initial.stderr
    script_path = episode / "script.json"
    script = json.loads(script_path.read_text(encoding="utf-8"))
    script["output_layout"] = [2, 3]
    _write_json(script_path, script)

    recomposed = _run("compose_episode.py", "--episode-dir", str(episode), "--mock")

    assert recomposed.returncode == 0, recomposed.stderr
    assert tuple(sorted(path.name for path in (episode / "final").glob("page-*.png"))) == (
        "page-01.png",
        "page-02.png",
    )


@pytest.mark.parametrize("output_layout", ([5], [2, 2]))
def test_output_layout_rejects_invalid_page_or_total(
    tmp_path: Path, output_layout: list[int]
) -> None:
    episode = _make_episode(tmp_path, (1, 1, 1, 1, 1))
    script_path = episode / "script.json"
    script = json.loads(script_path.read_text(encoding="utf-8"))
    script["output_layout"] = output_layout
    _write_json(script_path, script)

    composed = _run("compose_episode.py", "--episode-dir", str(episode), "--mock")

    assert composed.returncode == 1
    assert "output_layout" in composed.stderr
