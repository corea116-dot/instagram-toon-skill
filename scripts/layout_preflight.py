#!/usr/bin/env -S uv run --script
# /// script
# requires-python = ">=3.12"
# dependencies = ["pillow>=12.0", "pydantic>=2.12", "typer>=0.20"]
# ///
"""Measure final-page dialogue readability before image generation."""

from __future__ import annotations

import tempfile
from datetime import datetime
from pathlib import Path
from typing import Annotated, Literal

import typer
from content_review import layout_sha256, require_content_review
from delivery import grid_geometry
from episode_models import (
    CANVAS_HEIGHT,
    CANVAS_WIDTH,
    BriefModel,
    EpisodeScriptModel,
    NonBlankString,
    StrictModel,
)
from information_lock import require_content_lock
from PIL import Image
from pydantic import AwareDatetime, Field, ValidationError
from rendering import RenderError, find_korean_font, render_carousel, write_text_atomic

MIN_EFFECTIVE_FONT_SIZE = 34
DENSE_PANEL_CHARACTERS = 55


class BubblePreflightModel(StrictModel):
    page: Annotated[int, Field(ge=1)]
    group_size: Annotated[int, Field(ge=1, le=4)]
    panel: Annotated[int, Field(ge=1)]
    bubble: Annotated[int, Field(ge=1)]
    kind: Literal["bubble", "card"] = "bubble"
    element_id: str | None = None
    font_size: Annotated[int, Field(ge=1)]
    effective_font_size: Annotated[int, Field(ge=1)]
    text_characters: Annotated[int, Field(ge=1)]


class LayoutPreflightModel(StrictModel):
    schema_version: Literal["1.0"]
    episode_id: NonBlankString
    layout_sha256: NonBlankString
    checked_at: AwareDatetime
    minimum_effective_font_size: Annotated[int, Field(ge=1)]
    bubbles: tuple[BubblePreflightModel, ...]
    dense_pages: tuple[int, ...]
    issues: tuple[NonBlankString, ...]
    outcome: Literal["pass", "fail"]


def _modern_information_brief(episode_dir: Path) -> BriefModel | None:
    path = episode_dir / "brief.json"
    if not path.is_file():
        return None
    try:
        brief = BriefModel.model_validate_json(path.read_text(encoding="utf-8"))
    except (OSError, ValidationError):
        return None
    if brief.content_type == "informational" and brief.schema_version == "1.3":
        return brief
    return None


def _panel_scale(group_size: int, offset: int) -> float:
    if group_size == 1:
        return 1.0
    tile_sizes, _ = grid_geometry(group_size)
    width, height = tile_sizes[offset]
    return min(width / CANVAS_WIDTH, height / CANVAS_HEIGHT)


def run_layout_preflight(episode_dir: Path, *, draft: bool = False) -> tuple[Path, LayoutPreflightModel]:
    if not draft:
        require_content_review(episode_dir)
        require_content_lock(episode_dir)
    brief = _modern_information_brief(episode_dir)
    if brief is None:
        raise ValueError(
            "layout preflight is only required for informational brief schema 1.3"
        )
    script_path = episode_dir / "script.json"
    script = EpisodeScriptModel.model_validate_json(
        script_path.read_text(encoding="utf-8")
    )
    if script.output_layout is None:
        raise ValueError("layout preflight requires output_layout")
    bubbles: list[BubblePreflightModel] = []
    issues: list[str] = []
    dense_pages: list[int] = []
    next_panel = 0
    font_path = find_korean_font()
    with tempfile.TemporaryDirectory(prefix="instagram-toon-preflight-") as temp_dir:
        blank_path = Path(temp_dir) / "blank.png"
        Image.new("RGB", (CANVAS_WIDTH, CANVAS_HEIGHT), "white").save(blank_path)
        for page, group_size in enumerate(script.output_layout, start=1):
            dense_count = 0
            for offset in range(group_size):
                panel = script.panels[next_panel + offset]
                text_characters = sum(
                    len("".join(dialogue.text.split())) for dialogue in panel.dialogue
                )
                if panel.information_card:
                    text_characters += sum(len("".join(text.text.split())) for text in panel.information_card.texts)
                if text_characters > DENSE_PANEL_CHARACTERS:
                    dense_count += 1
                _, layouts = render_carousel(blank_path, panel, font_path, script.panel_sizes()[panel.panel - 1])
                scale = 1.0 if script.rendering_policy == "frame_native_v1" else _panel_scale(group_size, offset)
                for layout in layouts:
                    effective = round(layout.font_size * scale)
                    bubbles.append(
                        BubblePreflightModel(
                            page=page,
                            group_size=group_size,
                            panel=panel.panel,
                            bubble=layout.bubble,
                            kind=layout.kind,
                            element_id=layout.element_id,
                            font_size=layout.font_size,
                            effective_font_size=effective,
                            text_characters=text_characters,
                        )
                    )
                    if effective < MIN_EFFECTIVE_FONT_SIZE:
                        issues.append(
                            f"page {page} panel {panel.panel} {layout.kind} {layout.element_id or layout.bubble} effective "
                            f"font {effective}px is below {MIN_EFFECTIVE_FONT_SIZE}px"
                        )
            if group_size >= 3 and dense_count > 1:
                dense_pages.append(page)
                issues.append(
                    f"page {page} has {dense_count} dense panels in a {group_size}-panel group"
                )
            next_panel += group_size
    record = LayoutPreflightModel(
        schema_version="1.0",
        episode_id=script.episode_id,
        layout_sha256=layout_sha256(script_path),
        checked_at=datetime.now().astimezone(),
        minimum_effective_font_size=MIN_EFFECTIVE_FONT_SIZE,
        bubbles=tuple(bubbles),
        dense_pages=tuple(dense_pages),
        issues=tuple(issues),
        outcome="fail" if issues else "pass",
    )
    output = episode_dir / ("layout-diagnostic.json" if draft else "layout-preflight.json")
    write_text_atomic(output, record.model_dump_json(indent=2) + "\n")
    return output, record


def layout_preflight_issues(episode_dir: Path) -> tuple[str, ...]:
    brief = _modern_information_brief(episode_dir)
    if brief is None:
        return ()
    path = episode_dir / "layout-preflight.json"
    try:
        record = LayoutPreflightModel.model_validate_json(
            path.read_text(encoding="utf-8")
        )
        current_hash = layout_sha256(episode_dir / "script.json")
    except (OSError, ValidationError, ValueError) as error:
        return (f"layout preflight: {error}",)
    issues: list[str] = []
    if record.episode_id != brief.episode_id:
        issues.append("layout preflight episode_id does not match the brief")
    if record.layout_sha256 != current_hash:
        issues.append("layout preflight is stale: layout SHA-256 mismatch")
    if record.outcome != "pass":
        issues.extend(f"layout preflight failed: {issue}" for issue in record.issues)
    return tuple(issues)


def require_layout_preflight(episode_dir: Path) -> None:
    issues = layout_preflight_issues(episode_dir)
    if issues:
        raise ValueError("; ".join(issues))


def main(
    episode_dir: Annotated[
        Path,
        typer.Option("--episode-dir", exists=True, file_okay=False, resolve_path=True),
    ],
    draft: Annotated[bool, typer.Option("--draft")] = False,
) -> None:
    try:
        output, record = run_layout_preflight(episode_dir, draft=draft)
    except (OSError, RenderError, ValueError, ValidationError) as error:
        typer.echo(f"layout preflight failed for {episode_dir}: {error}", err=True)
        raise typer.Exit(code=1) from error
    if record.outcome != "pass":
        typer.echo(
            "layout preflight failed:\n"
            + "\n".join(f"- {issue}" for issue in record.issues),
            err=True,
        )
        raise typer.Exit(code=1)
    typer.echo(f"layout preflight passed: {output}")


if __name__ == "__main__":
    typer.run(main)
