from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import Final

from PIL import Image, ImageDraw, ImageOps

from episode_models import CANVAS_HEIGHT, CANVAS_WIDTH
from rendering import RenderError, save_png_atomic


GRID_BACKGROUND: Final = (255, 248, 237)
GRID_TILE_SIZE: Final = (492, 621)
GRID_POSITIONS: Final = ((36, 30), (552, 30), (36, 699), (552, 699))


@dataclass(frozen=True, slots=True)
class DeliveryPaths:
    rendered_panels: tuple[Path, ...]
    final_images: tuple[Path, ...]


def delivery_paths(episode_dir: Path, panel_count: int) -> DeliveryPaths:
    final_dir = episode_dir / "final"
    if panel_count == 4:
        return DeliveryPaths(
            rendered_panels=tuple(
                final_dir / f"carousel-{number}.png" for number in range(1, 5)
            ),
            final_images=(final_dir / "four-panel.png",),
        )
    if panel_count == 6:
        composed_dir = episode_dir / "composed"
        return DeliveryPaths(
            rendered_panels=tuple(
                composed_dir / f"panel-{number}.png" for number in range(1, 7)
            ),
            final_images=(
                final_dir / "opening.png",
                final_dir / "development-four-panel.png",
                final_dir / "ending.png",
            ),
        )
    raise RenderError(f"unsupported panel count: {panel_count}")


def _copy_panel(source_path: Path, output_path: Path) -> None:
    with Image.open(source_path) as source:
        save_png_atomic(source.convert("RGB"), output_path)


def _render_four_panel_grid(sources: tuple[Path, ...], output_path: Path) -> None:
    grid = Image.new("RGB", (CANVAS_WIDTH, CANVAS_HEIGHT), GRID_BACKGROUND)
    mask = Image.new("L", GRID_TILE_SIZE, 0)
    ImageDraw.Draw(mask).rounded_rectangle(
        (0, 0, GRID_TILE_SIZE[0] - 1, GRID_TILE_SIZE[1] - 1),
        radius=24,
        fill=255,
    )
    grid_draw = ImageDraw.Draw(grid)
    for source_path, position in zip(sources, GRID_POSITIONS, strict=True):
        with Image.open(source_path) as source:
            panel = ImageOps.contain(source.convert("RGB"), GRID_TILE_SIZE)
        tile = Image.new("RGB", GRID_TILE_SIZE, GRID_BACKGROUND)
        offset = (
            (GRID_TILE_SIZE[0] - panel.width) // 2,
            (GRID_TILE_SIZE[1] - panel.height) // 2,
        )
        tile.paste(panel, offset)
        grid.paste(tile, position, mask)
        grid_draw.rounded_rectangle(
            (
                position[0],
                position[1],
                position[0] + GRID_TILE_SIZE[0],
                position[1] + GRID_TILE_SIZE[1],
            ),
            radius=24,
            outline=(58, 48, 43),
            width=6,
        )
    save_png_atomic(grid, output_path)


def render_delivery(episode_dir: Path, panel_count: int, target: int | None) -> DeliveryPaths:
    paths = delivery_paths(episode_dir, panel_count)
    if panel_count == 4:
        _render_four_panel_grid(paths.rendered_panels, paths.final_images[0])
        return paths
    if target is None or target == 1:
        _copy_panel(paths.rendered_panels[0], paths.final_images[0])
    if target is None or 2 <= target <= 5:
        _render_four_panel_grid(paths.rendered_panels[1:5], paths.final_images[1])
    if target is None or target == 6:
        _copy_panel(paths.rendered_panels[5], paths.final_images[2])
    return paths


def clear_obsolete_six_panel_exports(episode_dir: Path) -> None:
    final_dir = episode_dir / "final"
    obsolete = (final_dir / "six-panel.png",) + tuple(
        final_dir / f"carousel-{number}.png" for number in range(1, 7)
    )
    for path in obsolete:
        path.unlink(missing_ok=True)
