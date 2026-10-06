from __future__ import annotations

from pathlib import Path

from pydantic import ValidationError

from episode_models import CompositionModel, EpisodeScriptModel, LayoutEntryModel
from rendering import RenderError


def load_script(episode_dir: Path) -> EpisodeScriptModel:
    path = episode_dir / "script.json"
    try:
        return EpisodeScriptModel.model_validate_json(path.read_text(encoding="utf-8"))
    except ValidationError as error:
        raise RenderError(f"invalid structured file {path}: {error}") from error


def require_complete_composition(
    episode_dir: Path, script: EpisodeScriptModel, required_paths: tuple[Path, ...]
) -> None:
    composition_path = episode_dir / "final" / "composition.json"
    missing = tuple(
        str(path) for path in (composition_path, *required_paths) if not path.is_file()
    )
    if missing:
        raise RenderError(
            "partial regeneration requires an existing full composition: "
            + ", ".join(missing)
        )
    composition = CompositionModel.model_validate_json(
        composition_path.read_text(encoding="utf-8")
    )
    if composition.rendering_policy != script.rendering_policy or (script.rendering_policy == "frame_native_v1" and composition.panel_sizes != script.panel_sizes()):
        raise RenderError("partial regeneration requires matching rendering policy and frame sizes")
    if composition.output_layout != script.output_layout:
        raise RenderError("partial regeneration requires a matching output_layout")


def merge_layouts(
    episode_dir: Path, target: int | None, new_entries: tuple[LayoutEntryModel, ...]
) -> tuple[LayoutEntryModel, ...]:
    if target is None:
        return tuple(sorted(new_entries, key=lambda item: (item.panel, item.kind, item.bubble)))
    path = episode_dir / "final" / "composition.json"
    previous = CompositionModel.model_validate_json(path.read_text(encoding="utf-8"))
    retained = tuple(item for item in previous.layouts if item.panel != target)
    return tuple(
        sorted(retained + new_entries, key=lambda item: (item.panel, item.kind, item.bubble))
    )
