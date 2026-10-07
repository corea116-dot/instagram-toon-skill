"""Approved #01 memo decoration inside the card's reserved rectangle.

Content, text fitting and presenter checks remain in the existing pipeline.
Versioned tokens are also available to a motion compositor without copying
the example's wording or rasterizing an entire comic page.
"""
from functools import lru_cache
import json
from pathlib import Path
import random

from PIL import ImageDraw

TOKENS_PATH = Path(__file__).resolve().parents[1] / "assets/information-cards/taped-memo-v1/style.json"


@lru_cache(maxsize=1)
def memo_tokens() -> dict:
    return json.loads(TOKENS_PATH.read_text(encoding="utf-8"))


def memo_font_path(role: str) -> Path:
    key = "label_and_emphasis" if role in ("label", "emphasis") else "body"
    return Path(__file__).resolve().parents[1] / memo_tokens()["fonts"][key]


def draw_taped_memo(draw: ImageDraw.ImageDraw, area) -> None:
    tokens = memo_tokens()
    colors = tokens["colors"]
    x, y, w, h = area.x, area.y, area.width, area.height
    scale = min(w / 1161, h / 530)
    stroke = max(1, round(tokens["geometry"]["stroke"] * scale))
    left, top, right, bottom = x + w*.01, y + h*.045, x + w*.982, y + h*.965
    shadow = [(left+w*.007, top+h*.014), (right+w*.009, top+h*.014),
              (right+w*.009, bottom+h*.017), (left+w*.007, bottom+h*.017)]
    draw.polygon(shadow, fill=colors["shadow"])
    rng = random.Random(tokens["geometry"]["seed"])
    wobble = max(.3, tokens["geometry"]["wobble"] * scale)
    points = []
    corners = [(left,top),(right,top),(right,bottom),(left,bottom),(left,top)]
    for a, b in zip(corners, corners[1:]):
        for step in range(13):
            t = step/13
            points.append((a[0]+(b[0]-a[0])*t+rng.uniform(-wobble,wobble),
                           a[1]+(b[1]-a[1])*t+rng.uniform(-wobble,wobble)))
    draw.polygon(points, fill=colors["paper"])
    draw.line(points+[points[0]], fill=colors["ink"], width=stroke, joint="curve")
    for start, end, slope in tokens["geometry"]["tapes"]:
        x1, x2 = x+w*start, x+w*end
        y1, y2 = y+h*.01, y+h*.085
        tilt = slope*h
        draw.polygon([(x1+2,y1),(x2,y1+tilt),(x2-2,y2),(x1,y2-tilt)], fill=colors["tape"])
        spacing = max(7, round(22*scale))
        for xx in range(round(x1+spacing/2),round(x2-4),spacing):
            draw.line([(xx,y1+4),(xx+max(2,round(5*scale)),y2-4)], fill=colors["tape_lines"], width=1)


def draw_memo_label(draw: ImageDraw.ImageDraw, area, accent: str) -> None:
    colors = memo_tokens()["colors"]
    bounds = (area.x,area.y,area.x+area.width,area.y+area.height)
    draw.rounded_rectangle(bounds, radius=min(16,area.height//4),
                           fill=colors[f"label_{accent}"], outline=colors["ink"], width=2)


def draw_memo_highlight(draw: ImageDraw.ImageDraw, ink_bounds: tuple, accent: str) -> None:
    left, top, right, bottom = ink_bounds
    if right <= left or bottom <= top:
        return
    h = bottom-top
    upper, lower = top+h*.24, top+h*.78
    draw.polygon([(left,upper+1),(right-2,upper),(right,lower-1),(left+2,lower)],
                 fill=memo_tokens()["colors"][f"marker_{accent}"])
