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

import json
from dataclasses import dataclass
from pathlib import Path
from typing import Annotated

import typer
from composition_state import load_script, merge_layouts, require_complete_composition
from delivery import (
    clear_obsolete_delivery_exports,
    delivery_paths,
    render_delivery,
)
from episode_models import (
    CANVAS_HEIGHT,
    CANVAS_WIDTH,
    BoxModel,
    CompositionModel,
    ContinuityModel,
    EpisodeScriptModel,
    LayoutEntryModel,
    PanelModel,
    PromptManifestModel,
    RenderMode,
)
from pydantic import ValidationError
from reference_policy import (
    CharacterReferencePolicy,
    load_character_policy,
    resolve_reference_paths,
    wardrobe_text_for_panel,
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
    "text, letters, numbers, captions, subtitles, speech bubbles, watermark, logo, "
    "different face shape, different beard shape, different hair, different body type, "
    "different age or gender presentation"
)
SKILL_ROOT = Path(__file__).resolve().parents[1]
VISUAL_STYLE_PATH = SKILL_ROOT / "memory" / "visual-style.json"
CHARACTER_BIBLE_PATH = SKILL_ROOT / "memory" / "character-bible.json"


@dataclass(frozen=True, slots=True)
class ComposeOptions:
    episode_dir: Path
    mock: bool
    panel: int | None


def _prompt_text(
    panel: PanelModel,
    character_policy: CharacterReferencePolicy,
    wardrobe_text: str,
) -> str:
    props = ", ".join(panel.props) if panel.props else "none"
    section = panel.section or "legacy"
    return (
        f"Section: {section}. Narrative beat: {panel.beat}. Scene: {panel.scene}. "
        f"Expression: {panel.expression}. Action: {panel.action}. "
        f"Props: {props}. Background: {panel.background}. Camera: {panel.camera}. "
        f"Character identity lock (must remain unchanged): {character_policy.identity_text} "
        f"Wardrobe and footwear state: {wardrobe_text} "
        "Character identity takes priority over style. Style may control only background, palette, texture, mood, and composition. Leave the declared speech-bubble safe areas uncluttered."
    )


def _revision_for(prompt_path: Path, partial: bool) -> int:
    if not partial or not prompt_path.is_file():
        return 0
    prompt = PromptManifestModel.model_validate_json(
        prompt_path.read_text(encoding="utf-8")
    )
    return prompt.revision + 1


def _primary_reference_images() -> tuple[str, ...]:
    try:
        visual_style = json.loads(VISUAL_STYLE_PATH.read_text(encoding="utf-8"))
        references = visual_style["reference_policy"]["primary_reference_images"]
    except (OSError, KeyError, TypeError, json.JSONDecodeError) as error:
        raise RenderError(
            f"invalid primary style references at {VISUAL_STYLE_PATH}: {error}"
        ) from error
    if not isinstance(references, list) or not references:
        raise RenderError(
            f"primary style references at {VISUAL_STYLE_PATH} must contain at least one path"
        )
    if not all(isinstance(reference, str) and reference for reference in references):
        raise RenderError(
            f"primary style references at {VISUAL_STYLE_PATH} must contain nonempty paths"
        )
    return resolve_reference_paths(
        tuple(references), SKILL_ROOT, "primary style references"
    )


def _reference_images_for(
    prompt_path: Path, canonical_references: tuple[str, ...], partial: bool
) -> tuple[str, ...]:
    if not partial or not prompt_path.is_file():
        return canonical_references
    existing = PromptManifestModel.model_validate_json(
        prompt_path.read_text(encoding="utf-8")
    )
    extras = tuple(
        reference
        for reference in existing.reference_images
        if reference not in canonical_references
        and reference != "assets/references/styles"
        and not reference.startswith(("assets/references/current/", "assets/references/styles/"))
    )
    return canonical_references + tuple(dict.fromkeys(extras))


def _prompt_manifest(
    script: EpisodeScriptModel,
    panel: PanelModel,
    mode: RenderMode,
    revision: int,
    reference_images: tuple[str, ...],
    character_policy: CharacterReferencePolicy,
) -> PromptManifestModel:
    previous = script.panels[panel.panel - 2] if panel.panel > 1 else None
    continuity = ContinuityModel(
        previous_panel=previous.panel if previous else None,
        locked_characters=character_policy.character_ids,
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
        prompt=_prompt_text(
            panel,
            character_policy,
            wardrobe_text_for_panel(character_policy, panel.panel, script.panels),
        ),
        negative_prompt=NEGATIVE_PROMPT,
        reference_images=reference_images,
        bubble_safe_areas=safe_areas,
        continuity=continuity,
    )


def _preflight_partial(episode_dir: Path, script: EpisodeScriptModel) -> None:
    paths = delivery_paths(
        episode_dir, len(script.panels), script.output_layout
    )
    require_complete_composition(episode_dir, script, paths.rendered_panels + paths.final_images)


def compose(options: ComposeOptions) -> Path:
    script = load_script(options.episode_dir)
    character_policy = load_character_policy(
        options.episode_dir, CHARACTER_BIBLE_PATH, SKILL_ROOT
    )
    reference_images = tuple(
        dict.fromkeys(character_policy.reference_images + _primary_reference_images())
    )
    if options.panel is not None:
        if options.panel > len(script.panels):
            raise RenderError(
                f"panel {options.panel} does not exist in this {len(script.panels)}-panel script"
            )
        _preflight_partial(options.episode_dir, script)
    prompts_dir = options.episode_dir / "prompts"
    raw_dir = options.episode_dir / "raw"
    final_dir = options.episode_dir / "final"
    paths = delivery_paths(
        options.episode_dir, len(script.panels), script.output_layout
    )
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
                character_policy,
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
    merged = merge_layouts(options.episode_dir, options.panel, tuple(layouts))
    manifest = CompositionModel(
        schema_version="1.1" if script.output_layout is not None else "1.0",
        canvas=(CANVAS_WIDTH, CANVAS_HEIGHT),
        layouts=merged,
        output_layout=script.output_layout,
    )
    write_text_atomic(
        final_dir / "composition.json", manifest.model_dump_json(indent=2) + "\n"
    )
    _ = render_delivery(
        options.episode_dir,
        len(script.panels),
        script.output_layout,
        options.panel,
    )
    if options.panel is None:
        clear_obsolete_delivery_exports(options.episode_dir, paths)
    return final_dir


def main(
    episode_dir: Annotated[
        Path,
        typer.Option("--episode-dir", exists=True, file_okay=False, resolve_path=True),
    ],
    mock: Annotated[bool, typer.Option("--mock")] = False,
    panel: Annotated[int | None, typer.Option("--panel", min=1)] = None,
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
