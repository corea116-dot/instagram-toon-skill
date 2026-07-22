from __future__ import annotations

from dataclasses import dataclass
import hashlib
from math import ceil
import os
from pathlib import Path
import tempfile
from typing import Final

from PIL import Image, ImageDraw, ImageFont, ImageOps

from episode_models import (
    BoxModel,
    CANVAS_HEIGHT,
    CANVAS_WIDTH,
    DialogueModel,
    LayoutEntryModel,
    PanelModel,
)


FONT_CANDIDATES: Final = (
    Path("/System/Library/Fonts/AppleSDGothicNeo.ttc"),
    Path("/System/Library/Fonts/Supplemental/AppleGothic.ttf"),
    Path("/System/Library/Fonts/Supplemental/Arial Unicode.ttf"),
    Path("/usr/share/fonts/opentype/noto/NotoSansCJK-Regular.ttc"),
    Path("/usr/share/fonts/truetype/noto/NotoSansCJK-Regular.ttc"),
    Path("C:/Windows/Fonts/malgun.ttf"),
)
PALETTE: Final = (
    (244, 225, 210),
    (219, 229, 245),
    (232, 222, 242),
    (217, 239, 230),
    (249, 232, 201),
)
PADDING: Final = 28
TAIL_HEIGHT: Final = 22
MIN_FONT_SIZE: Final = 26
MAX_FONT_SIZE: Final = 56


@dataclass(frozen=True, slots=True)
class RenderError(Exception):
    detail: str

    def __str__(self) -> str:
        return self.detail


@dataclass(frozen=True, slots=True)
class FittedText:
    font: ImageFont.FreeTypeFont
    font_size: int
    lines: tuple[str, ...]
    line_height: int
    box: BoxModel


@dataclass(frozen=True, slots=True)
class TextMeasurer:
    draw: ImageDraw.ImageDraw
    font: ImageFont.FreeTypeFont

    def width(self, text: str) -> float:
        return self.draw.textlength(text, font=self.font)

    def wrap(self, text: str, max_width: int) -> tuple[str, ...]:
        lines: list[str] = []
        for paragraph in text.split("\n"):
            current = ""
            for character in paragraph:
                candidate = current + character
                if self.width(candidate) <= max_width:
                    current = candidate
                    continue
                split_at = current.rfind(" ")
                if split_at > 0:
                    lines.append(current[:split_at].rstrip())
                    current = current[split_at + 1 :].lstrip() + character
                else:
                    if not current:
                        raise RenderError(
                            "a glyph is wider than the speech-bubble text area"
                        )
                    lines.append(current.rstrip())
                    current = character.lstrip()
            if current or not lines:
                lines.append(current.rstrip())
        return tuple(lines)


def find_korean_font() -> Path:
    configured = os.environ.get("INSTAGRAM_TOON_FONT")
    candidates = (Path(configured),) if configured else FONT_CANDIDATES
    for path in candidates:
        if path.is_file():
            font = ImageFont.truetype(str(path), size=32)
            if font.getmask("한글").getbbox() is not None:
                return path
    detail = (
        "Korean font not found; set INSTAGRAM_TOON_FONT to a Korean TTF or TTC file"
    )
    raise RenderError(detail)


def _fit_text(
    draw: ImageDraw.ImageDraw, font_path: Path, dialogue: DialogueModel
) -> FittedText:
    max_text_width = dialogue.width - (PADDING * 2)
    for font_size in range(MAX_FONT_SIZE, MIN_FONT_SIZE - 1, -2):
        font = ImageFont.truetype(str(font_path), size=font_size)
        measurer = TextMeasurer(draw=draw, font=font)
        lines = measurer.wrap(dialogue.text, max_text_width)
        line_height = font_size + 12
        text_width = ceil(max(measurer.width(line) for line in lines))
        bubble_width = max(220, text_width + (PADDING * 2))
        bubble_height = (len(lines) * line_height) + (PADDING * 2) + TAIL_HEIGHT
        if bubble_width <= dialogue.width and bubble_height <= dialogue.height:
            box = BoxModel(
                x=dialogue.x + ((dialogue.width - bubble_width) // 2),
                y=dialogue.y + ((dialogue.height - bubble_height) // 2),
                width=bubble_width,
                height=bubble_height,
            )
            return FittedText(
                font=font,
                font_size=font_size,
                lines=lines,
                line_height=line_height,
                box=box,
            )
    raise RenderError(f"dialogue does not fit its safe area: {dialogue.text!r}")


def render_carousel(
    raw_path: Path, panel: PanelModel, font_path: Path
) -> tuple[Image.Image, tuple[LayoutEntryModel, ...]]:
    with Image.open(raw_path) as source:
        canvas = ImageOps.fit(source.convert("RGB"), (CANVAS_WIDTH, CANVAS_HEIGHT))
    draw = ImageDraw.Draw(canvas)
    layouts: list[LayoutEntryModel] = []
    for bubble_index, dialogue in enumerate(panel.dialogue, start=1):
        fitted = _fit_text(draw, font_path, dialogue)
        box = fitted.box
        body_bottom = box.y + box.height - TAIL_HEIGHT
        draw.rounded_rectangle(
            (box.x, box.y, box.x + box.width, body_bottom),
            radius=32,
            fill=(255, 255, 255),
            outline=(35, 38, 47),
            width=4,
        )
        tail_x = box.x + (box.width // 3)
        draw.polygon(
            (
                (tail_x - 18, body_bottom - 2),
                (tail_x + 18, body_bottom - 2),
                (tail_x, box.y + box.height),
            ),
            fill=(255, 255, 255),
            outline=(35, 38, 47),
        )
        text_y = box.y + PADDING
        measurer = TextMeasurer(draw=draw, font=fitted.font)
        for line in fitted.lines:
            text_x = box.x + ((box.width - ceil(measurer.width(line))) // 2)
            draw.text((text_x, text_y), line, font=fitted.font, fill=(27, 31, 38))
            text_y += fitted.line_height
        layouts.append(
            LayoutEntryModel(
                panel=panel.panel,
                bubble=bubble_index,
                box=box,
                safe_area=BoxModel(
                    x=dialogue.x,
                    y=dialogue.y,
                    width=dialogue.width,
                    height=dialogue.height,
                ),
                font_size=fitted.font_size,
                lines=fitted.lines,
            )
        )
    return canvas, tuple(layouts)


def render_mock(episode_id: str, panel: PanelModel, revision: int) -> Image.Image:
    seed_text = f"{episode_id}:{panel.model_dump_json()}:{revision}"
    digest = hashlib.sha256(seed_text.encode("utf-8")).digest()
    background = PALETTE[digest[0] % len(PALETTE)]
    image = Image.new("RGB", (CANVAS_WIDTH, CANVAS_HEIGHT), background)
    draw = ImageDraw.Draw(image)
    draw.rectangle((0, 900, CANVAS_WIDTH, CANVAS_HEIGHT), fill=(189, 165, 146))
    draw.rectangle(
        (90, 175, 390, 520), fill=(67, 80, 116), outline=(245, 238, 213), width=18
    )
    draw.ellipse((235, 245, 330, 340), fill=(255, 239, 165))
    bed_color = PALETTE[digest[1] % len(PALETTE)]
    draw.rounded_rectangle(
        (140, 770, 990, 1190), radius=70, fill=bed_color, outline=(75, 69, 78), width=10
    )
    person_x = 390 + (digest[2] % 130)
    draw.ellipse(
        (person_x, 530, person_x + 250, 780),
        fill=(247, 203, 172),
        outline=(61, 53, 60),
        width=8,
    )
    draw.pieslice(
        (person_x - 15, 500, person_x + 265, 745), 180, 355, fill=(59, 45, 48)
    )
    eye_y = 655
    draw.ellipse((person_x + 65, eye_y, person_x + 82, eye_y + 17), fill=(45, 42, 48))
    draw.ellipse((person_x + 165, eye_y, person_x + 182, eye_y + 17), fill=(45, 42, 48))
    phone_x = 640 + (digest[3] % 90)
    phone_y = 720 + (revision * 13 % 80)
    draw.rounded_rectangle(
        (phone_x, phone_y, phone_x + 125, phone_y + 225),
        radius=22,
        fill=(37, 45, 59),
        outline=(235, 242, 250),
        width=8,
    )
    draw.ellipse(
        (phone_x - 115, phone_y + 90, phone_x - 5, phone_y + 200),
        fill=(247, 203, 172),
        outline=(61, 53, 60),
        width=7,
    )
    return image


def save_png_atomic(image: Image.Image, path: Path) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    handle = tempfile.NamedTemporaryFile(dir=path.parent, suffix=".tmp", delete=False)
    temporary = Path(handle.name)
    handle.close()
    try:
        image.save(temporary, format="PNG", optimize=False, compress_level=9)
        temporary.replace(path)
        temporary = Path()
    finally:
        if temporary != Path():
            temporary.unlink(missing_ok=True)


def write_text_atomic(path: Path, text: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    handle = tempfile.NamedTemporaryFile(
        dir=path.parent, suffix=".tmp", mode="w", encoding="utf-8", delete=False
    )
    temporary = Path(handle.name)
    try:
        with handle:
            handle.write(text)
        temporary.replace(path)
        temporary = Path()
    finally:
        if temporary != Path():
            temporary.unlink(missing_ok=True)
