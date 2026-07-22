#!/usr/bin/env -S uv run --script
# /// script
# requires-python = ">=3.12"
# dependencies = [
#     "pillow>=12.0",
#     "pydantic>=2.12",
#     "typer>=0.20",
# ]
# ///

# ─── How to run ───
# 1. Install uv (if not installed):
#      curl -LsSf https://astral.sh/uv/install.sh | sh
# 2. Run directly (no venv, no pip install needed):
#      uv run scripts/compose_episode.py --episode-dir episodes/EP-001-title --mock
# 3. Or make executable and run:
#      chmod +x scripts/compose_episode.py && ./scripts/compose_episode.py --episode-dir episodes/EP-001-title --mock
# ──────────────────

from __future__ import annotations

from dataclasses import dataclass
import json
from pathlib import Path
from typing import Annotated

from pydantic import ValidationError
import typer

from delivery import (
    clear_obsolete_six_panel_exports,
    delivery_paths,
    render_delivery,
)
from episode_models import (
    BoxModel,
    CANVAS_HEIGHT,
    CANVAS_WIDTH,
    CompositionModel,
    ContinuityModel,
    EpisodeScriptModel,
    LayoutEntryModel,
    PanelModel,
    PromptManifestModel,
    RenderMode,
)
from rendering import (
    RenderError,
    find_korean_font,
    render_carousel,
    render_mock,
    save_png_atomic,
    write_text_atomic,
)


NEGATIVE_PROMPT = (
    "text, letters, numbers, captions, subtitles, speech bubbles, watermark, logo"
)
SKILL_ROOT = Path(__file__).resolve().parents[1]
VISUAL_STYLE_PATH = SKILL_ROOT / "memory" / "visual-style.json"


@dataclass(frozen=True, slots=True)
class ComposeOptions:
    episode_dir: Path
    mock: bool
    panel: int | None


def _load_script(episode_dir: Path) -> EpisodeScriptModel:
    path = episode_dir / "script.json"
    try:
        return EpisodeScriptModel.model_validate_json(path.read_text(encoding="utf-8"))
    except ValidationError as error:
        raise RenderError(f"invalid structured file {path}: {error}") from error


def _prompt_text(panel: PanelModel) -> str:
    props = ", ".join(panel.props) if panel.props else "none"
    section = panel.section or "legacy"
    return (
        f"Section: {section}. Narrative beat: {panel.beat}. Scene: {panel.scene}. "
        f"Expression: {panel.expression}. Action: {panel.action}. "
        f"Props: {props}. Background: {panel.background}. Camera: {panel.camera}. "
        "Keep the established character and visual style consistent. Leave the declared speech-bubble safe areas uncluttered."
    )


def _revision_for(prompt_path: Path, partial: bool) -> int:
    if not partial or not prompt_path.is_file():
        return 0
    prompt = PromptManifestModel.model_validate_json(
        prompt_path.read_text(encoding="utf-8")
    )
    return prompt.revision + 1


def _primary_reference_images() -> tuple[str, str, str]:
    try:
        visual_style = json.loads(VISUAL_STYLE_PATH.read_text(encoding="utf-8"))
        references = visual_style["reference_policy"]["primary_reference_images"]
    except (OSError, KeyError, TypeError, json.JSONDecodeError) as error:
        raise RenderError(
            f"invalid primary style references at {VISUAL_STYLE_PATH}: {error}"
        ) from error
    if not isinstance(references, list) or len(references) < 3:
        raise RenderError(
            f"primary style references at {VISUAL_STYLE_PATH} must contain at least three paths"
        )
    skill_root = SKILL_ROOT.resolve()
    for index, reference in enumerate(references[:3], start=1):
        if not isinstance(reference, str) or not reference:
            raise RenderError(
                f"primary style reference {index} at {VISUAL_STYLE_PATH} must be a nonempty path"
            )
        configured_path = Path(reference)
        if configured_path.is_absolute():
            raise RenderError(
                f"primary style reference {reference!r} must be relative to {SKILL_ROOT}"
            )
        if any(part == ".." for part in configured_path.parts):
            raise RenderError(
                f"primary style reference {reference!r} must not contain path traversal"
            )
        try:
            resolved_path = (SKILL_ROOT / configured_path).resolve()
        except (OSError, RuntimeError) as error:
            raise RenderError(
                f"primary style reference {reference!r} could not be resolved: {error}"
            ) from error
        if not resolved_path.is_relative_to(skill_root):
            raise RenderError(
                f"primary style reference {reference!r} escapes skill root {SKILL_ROOT}"
            )
        if not resolved_path.is_file():
            raise RenderError(
                f"primary style reference {reference!r} is not a regular file under {SKILL_ROOT}"
            )
    first, second, third = references[:3]
    return first, second, third


def _reference_images_for(
    prompt_path: Path, primary_references: tuple[str, str, str], partial: bool
) -> tuple[str, ...]:
    if not partial or not prompt_path.is_file():
        return primary_references
    existing = PromptManifestModel.model_validate_json(
        prompt_path.read_text(encoding="utf-8")
    )
    extras = tuple(
        reference
        for reference in existing.reference_images
        if reference not in primary_references
    )
    return primary_references + extras


def _prompt_manifest(
    script: EpisodeScriptModel,
    panel: PanelModel,
    mode: RenderMode,
    revision: int,
    reference_images: tuple[str, ...],
) -> PromptManifestModel:
    previous = script.panels[panel.panel - 2] if panel.panel > 1 else None
    continuity = ContinuityModel(
        previous_panel=previous.panel if previous else None,
        locked_characters=(),
        locked_props=previous.props if previous else (),
    )
    safe_areas = tuple(
        BoxModel(x=item.x, y=item.y, width=item.width, height=item.height)
        for item in panel.dialogue
    )
    return PromptManifestModel(
        schema_version="1.0",
        panel=panel.panel,
        revision=revision,
        mode=mode,
        size=(CANVAS_WIDTH, CANVAS_HEIGHT),
        prompt=_prompt_text(panel),
        negative_prompt=NEGATIVE_PROMPT,
        reference_images=reference_images,
        bubble_safe_areas=safe_areas,
        continuity=continuity,
    )


def _preflight_partial(episode_dir: Path, panel_count: int) -> None:
    paths = delivery_paths(episode_dir, panel_count)
    required = [episode_dir / "final" / "composition.json"]
    required.extend(paths.rendered_panels + paths.final_images)
    missing = tuple(str(path) for path in required if not path.is_file())
    if missing:
        raise RenderError(
            "partial regeneration requires an existing full composition: "
            + ", ".join(missing)
        )


def _merged_layouts(
    episode_dir: Path, target: int | None, new_entries: tuple[LayoutEntryModel, ...]
) -> tuple[LayoutEntryModel, ...]:
    if target is None:
        return tuple(sorted(new_entries, key=lambda item: (item.panel, item.bubble)))
    path = episode_dir / "final" / "composition.json"
    previous = CompositionModel.model_validate_json(path.read_text(encoding="utf-8"))
    retained = tuple(item for item in previous.layouts if item.panel != target)
    return tuple(
        sorted(retained + new_entries, key=lambda item: (item.panel, item.bubble))
    )


def compose(options: ComposeOptions) -> Path:
    script = _load_script(options.episode_dir)
    reference_images = _primary_reference_images()
    if options.panel is not None:
        if options.panel > len(script.panels):
            raise RenderError(
                f"panel {options.panel} does not exist in this {len(script.panels)}-panel script"
            )
        _preflight_partial(options.episode_dir, len(script.panels))
    prompts_dir = options.episode_dir / "prompts"
    raw_dir = options.episode_dir / "raw"
    final_dir = options.episode_dir / "final"
    paths = delivery_paths(options.episode_dir, len(script.panels))
    rendered_dir = paths.rendered_panels[0].parent
    for path in (prompts_dir, raw_dir, rendered_dir, final_dir):
        path.mkdir(parents=True, exist_ok=True)
    selected = (
        script.panels if options.panel is None else (script.panels[options.panel - 1],)
    )
    mode: RenderMode = "mock" if options.mock else "native"
    font_path = find_korean_font()
    layouts: list[LayoutEntryModel] = []
    for panel in selected:
        prompt_path = prompts_dir / f"panel-{panel.panel}.json"
        partial = options.panel is not None
        revision = _revision_for(prompt_path, partial) if partial else 0
        if options.mock or partial or not prompt_path.is_file():
            prompt = _prompt_manifest(
                script,
                panel,
                mode,
                revision,
                _reference_images_for(
                    prompt_path, reference_images, partial
                ),
            )
            write_text_atomic(prompt_path, prompt.model_dump_json(indent=2) + "\n")
        raw_path = raw_dir / f"panel-{panel.panel}.png"
        if options.mock:
            save_png_atomic(render_mock(script.episode_id, panel, revision), raw_path)
        elif not raw_path.is_file():
            raise RenderError(f"raw panel is missing: {raw_path}")
        carousel, panel_layouts = render_carousel(raw_path, panel, font_path)
        save_png_atomic(carousel, paths.rendered_panels[panel.panel - 1])
        layouts.extend(panel_layouts)
    merged = _merged_layouts(options.episode_dir, options.panel, tuple(layouts))
    manifest = CompositionModel(
        schema_version="1.0", canvas=(CANVAS_WIDTH, CANVAS_HEIGHT), layouts=merged
    )
    write_text_atomic(
        final_dir / "composition.json", manifest.model_dump_json(indent=2) + "\n"
    )
    _ = render_delivery(options.episode_dir, len(script.panels), options.panel)
    if len(script.panels) == 6 and options.panel is None:
        clear_obsolete_six_panel_exports(options.episode_dir)
    return final_dir


def main(
    episode_dir: Annotated[
        Path,
        typer.Option("--episode-dir", exists=True, file_okay=False, resolve_path=True),
    ],
    mock: Annotated[bool, typer.Option("--mock")] = False,
    panel: Annotated[int | None, typer.Option("--panel", min=1, max=6)] = None,
) -> None:
    try:
        result = compose(
            ComposeOptions(episode_dir=episode_dir, mock=mock, panel=panel)
        )
    except (OSError, RenderError, ValidationError) as error:
        typer.echo(f"compose failed for {episode_dir}: {error}", err=True)
        raise typer.Exit(code=1) from error
    typer.echo(f"composed episode: {result}")


if __name__ == "__main__":
    typer.run(main)
