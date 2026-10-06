from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import Final

from episode_models import CANVAS_HEIGHT, CANVAS_WIDTH
from PIL import Image, ImageDraw, ImageOps
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


def _layout_pages(
    final_dir: Path, output_layout: tuple[int, ...]
) -> tuple[DeliveryPage, ...]:
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


from frame_geometry import grid_geometry


def _render_grid(sources: tuple[Path, ...], output_path: Path, *, native: bool = False) -> None:
    tile_sizes, positions = grid_geometry(len(sources))
    grid = Image.new("RGB", (CANVAS_WIDTH, CANVAS_HEIGHT), GRID_BACKGROUND)
    grid_draw = ImageDraw.Draw(grid)
    for source_path, tile_size, position in zip(
        sources, tile_sizes, positions, strict=True
    ):
        with Image.open(source_path) as source:
            if native and source.size != tile_size:
                raise RenderError(f"native composed panel must be {tile_size}, got {source.size}")
            panel = source.convert("RGB") if native else ImageOps.contain(source.convert("RGB"), tile_size)
        if native:
            # Border lives entirely in the gutter, never on lettered pixels.
            grid_draw.rectangle(
                (position[0] - 6, position[1] - 6,
                 position[0] + tile_size[0] + 5, position[1] + tile_size[1] + 5),
                outline=(58, 48, 43), width=6,
            )
            grid.paste(panel, position)
            continue
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
    rendering_policy: str = "legacy_contain",
) -> DeliveryPaths:
    paths = delivery_paths(episode_dir, panel_count, output_layout)
    for page in paths.pages:
        if target is None or target in page.panel_numbers:
            sources = tuple(
                paths.rendered_panels[number - 1] for number in page.panel_numbers
            )
            if len(sources) == 1:
                if rendering_policy == "frame_native_v1":
                    with Image.open(sources[0]) as source:
                        if source.size != (CANVAS_WIDTH, CANVAS_HEIGHT):
                            raise RenderError("native single panel size mismatch")
                _copy_panel(sources[0], page.output_path)
            else:
                _render_grid(sources, page.output_path, native=rendering_policy == "frame_native_v1")
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
