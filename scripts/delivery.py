from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import Final

from PIL import Image, ImageDraw, ImageOps

from episode_models import CANVAS_HEIGHT, CANVAS_WIDTH
from rendering import RenderError, save_png_atomic


GRID_BACKGROUND: Final = (255, 248, 237)


@dataclass(frozen=True, slots=True)
class DeliveryPage:
    panel_numbers: tuple[int, ...]
    output_path: Path


@dataclass(frozen=True, slots=True)
class DeliveryPaths:
    rendered_panels: tuple[Path, ...]
    pages: tuple[DeliveryPage, ...]

    @property
    def final_images(self) -> tuple[Path, ...]:
        return tuple(page.output_path for page in self.pages)


def delivery_paths(
    episode_dir: Path, panel_count: int, output_layout: tuple[int, ...] | None
) -> DeliveryPaths:
    final_dir = episode_dir / "final"
    if output_layout is not None:
        composed_dir = episode_dir / "composed"
        return DeliveryPaths(
            rendered_panels=tuple(
                composed_dir / f"panel-{number}.png"
                for number in range(1, panel_count + 1)
            ),
            pages=_layout_pages(final_dir, output_layout),
        )
    if panel_count == 4:
        return DeliveryPaths(
            rendered_panels=tuple(
                final_dir / f"carousel-{number}.png" for number in range(1, 5)
            ),
            pages=(
                DeliveryPage(
                    panel_numbers=(1, 2, 3, 4), output_path=final_dir / "four-panel.png"
                ),
            ),
        )
    if panel_count == 6:
        composed_dir = episode_dir / "composed"
        return DeliveryPaths(
            rendered_panels=tuple(
                composed_dir / f"panel-{number}.png" for number in range(1, 7)
            ),
            pages=(
                DeliveryPage((1,), final_dir / "opening.png"),
                DeliveryPage((2, 3, 4, 5), final_dir / "development-four-panel.png"),
                DeliveryPage((6,), final_dir / "ending.png"),
            ),
        )
    raise RenderError(f"unsupported legacy panel count: {panel_count}")


def _layout_pages(final_dir: Path, output_layout: tuple[int, ...]) -> tuple[DeliveryPage, ...]:
    next_panel = 1
    pages: list[DeliveryPage] = []
    for page_number, panel_total in enumerate(output_layout, start=1):
        panel_numbers = tuple(range(next_panel, next_panel + panel_total))
        pages.append(
            DeliveryPage(panel_numbers, final_dir / f"page-{page_number:02}.png")
        )
        next_panel += panel_total
    return tuple(pages)


def _copy_panel(source_path: Path, output_path: Path) -> None:
    with Image.open(source_path) as source:
        save_png_atomic(source.convert("RGB"), output_path)


def _grid_geometry(
    count: int,
) -> tuple[tuple[tuple[int, int], ...], tuple[tuple[int, int], ...]]:
    match count:
        case 2:
            return ((1008, 630), (1008, 630)), ((36, 30), (36, 690))
        case 3:
            return (
                ((1008, 594), (492, 660), (492, 660)),
                ((36, 30), (36, 660), (552, 660)),
            )
        case 4:
            return (
                ((492, 621),) * 4,
                ((36, 30), (552, 30), (36, 699), (552, 699)),
            )
        case _:
            raise RenderError(f"unsupported page layout: {count} panels")


def _render_grid(sources: tuple[Path, ...], output_path: Path) -> None:
    tile_sizes, positions = _grid_geometry(len(sources))
    grid = Image.new("RGB", (CANVAS_WIDTH, CANVAS_HEIGHT), GRID_BACKGROUND)
    grid_draw = ImageDraw.Draw(grid)
    for source_path, tile_size, position in zip(sources, tile_sizes, positions, strict=True):
        with Image.open(source_path) as source:
            panel = ImageOps.contain(source.convert("RGB"), tile_size)
        tile = Image.new("RGB", tile_size, GRID_BACKGROUND)
        offset = (
            (tile_size[0] - panel.width) // 2,
            (tile_size[1] - panel.height) // 2,
        )
        tile.paste(panel, offset)
        mask = Image.new("L", tile_size, 0)
        ImageDraw.Draw(mask).rounded_rectangle(
            (0, 0, tile_size[0] - 1, tile_size[1] - 1), radius=24, fill=255
        )
        grid.paste(tile, position, mask)
        grid_draw.rounded_rectangle(
            (
                position[0],
                position[1],
                position[0] + tile_size[0],
                position[1] + tile_size[1],
            ),
            radius=24,
            outline=(58, 48, 43),
            width=6,
        )
    save_png_atomic(grid, output_path)


def render_delivery(
    episode_dir: Path,
    panel_count: int,
    output_layout: tuple[int, ...] | None,
    target: int | None,
) -> DeliveryPaths:
    paths = delivery_paths(episode_dir, panel_count, output_layout)
    for page in paths.pages:
        if target is None or target in page.panel_numbers:
            sources = tuple(paths.rendered_panels[number - 1] for number in page.panel_numbers)
            if len(sources) == 1:
                _copy_panel(sources[0], page.output_path)
            else:
                _render_grid(sources, page.output_path)
    return paths


def clear_obsolete_delivery_exports(episode_dir: Path, paths: DeliveryPaths) -> None:
    final_dir = episode_dir / "final"
    retained = set(paths.rendered_panels + paths.final_images)
    known_exports = {
        final_dir / "four-panel.png",
        final_dir / "six-panel.png",
        final_dir / "opening.png",
        final_dir / "development-four-panel.png",
        final_dir / "ending.png",
        *(final_dir / f"carousel-{number}.png" for number in range(1, 7)),
        *final_dir.glob("page-*.png"),
    }
    for path in known_exports - retained:
        path.unlink(missing_ok=True)
