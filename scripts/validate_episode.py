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
#      uv run scripts/validate_episode.py --episode-dir episodes/EP-001-title
# 3. Or make executable and run:
#      chmod +x scripts/validate_episode.py && ./scripts/validate_episode.py --episode-dir episodes/EP-001-title
# ──────────────────

from __future__ import annotations

from pathlib import Path
from typing import Annotated

import typer
from content_review import content_review_issues
from delivery import delivery_paths
from episode_models import (
    CANVAS_HEIGHT,
    CANVAS_WIDTH,
    BriefModel,
    CompositionModel,
    EpisodeScriptModel,
    PromptManifestModel,
    boxes_overlap,
)
from information_lock import content_lock_issues
from instagram_link_validation import (
    instagram_link_issues,
    requires_instagram_link_analysis,
)
from language_policy import (
    hard_banned_issues,
    language_policy_issues,
    review_required_findings,
)
from layout_preflight import layout_preflight_issues, _panel_scale, MIN_EFFECTIVE_FONT_SIZE
from PIL import Image, UnidentifiedImageError
from pydantic import ValidationError
from qa_reporting import QaSupplemental, existing_agent_section, qa_report_text
from rendering import write_text_atomic
from story_module_validation import story_module_issues, story_module_summary
from topic_research_validation import requires_topic_research, topic_research_issues

DEFAULT_PANEL_COUNT = 6
DEFAULT_OUTPUT_LAYOUT: tuple[int, ...] | None = None
DeliveryConfig = tuple[int, tuple[int, ...] | None]


def _delivery_config(episode_dir: Path) -> DeliveryConfig | None:
    path = episode_dir / "script.json"
    if not path.is_file():
        return DEFAULT_PANEL_COUNT, DEFAULT_OUTPUT_LAYOUT
    try:
        script = EpisodeScriptModel.model_validate_json(
            path.read_text(encoding="utf-8")
        )
    except (OSError, ValidationError):
        return None
    return len(script.panels), script.output_layout


def _required_paths(
    episode_dir: Path,
    delivery_config: DeliveryConfig | None,
    requires_topic_research: bool,
    requires_instagram_link_analysis: bool,
) -> tuple[Path, ...]:
    paths = [
        episode_dir / "brief.json",
        episode_dir / "script.json",
        episode_dir / "caption.txt",
    ]
    if requires_topic_research:
        paths.append(episode_dir / "topic-research.json")
    if requires_instagram_link_analysis:
        paths.append(episode_dir / "instagram-source.json")
    if delivery_config is not None:
        panel_count, output_layout = delivery_config
        delivery = delivery_paths(episode_dir, panel_count, output_layout)
        paths.extend(
            episode_dir / "prompts" / f"panel-{number}.json"
            for number in range(1, panel_count + 1)
        )
        paths.extend(
            episode_dir / "raw" / f"panel-{number}.png"
            for number in range(1, panel_count + 1)
        )
        paths.append(episode_dir / "final" / "composition.json")
        paths.extend(delivery.rendered_panels)
        paths.extend(delivery.final_images)
    return tuple(paths)


def _check_models(episode_dir: Path) -> tuple[str, ...]:
    issues: list[str] = []
    models = (
        (episode_dir / "brief.json", BriefModel),
        (episode_dir / "script.json", EpisodeScriptModel),
    )
    for path, model in models:
        if not path.is_file():
            continue
        try:
            _ = model.model_validate_json(path.read_text(encoding="utf-8"))
        except (OSError, ValidationError) as error:
            issues.append(f"invalid structured file {path}: {error}")
    caption = episode_dir / "caption.txt"
    if caption.is_file() and not caption.read_text(encoding="utf-8").strip():
        issues.append(f"empty caption: {caption}")
    return tuple(issues)


def _check_brief_script_layout(episode_dir: Path) -> tuple[str, ...]:
    brief_path = episode_dir / "brief.json"
    script_path = episode_dir / "script.json"
    if not brief_path.is_file() or not script_path.is_file():
        return ()
    try:
        brief = BriefModel.model_validate_json(brief_path.read_text(encoding="utf-8"))
        script = EpisodeScriptModel.model_validate_json(
            script_path.read_text(encoding="utf-8")
        )
    except (OSError, ValidationError):
        return ()
    if brief.output_layout is not None and brief.output_layout != script.output_layout:
        return ("brief output_layout does not match script output_layout",)
    return ()


def _image_issue(path: Path, exact_size: bool) -> str | None:
    try:
        with Image.open(path) as image:
            _ = image.load()
            size = image.size
            image_format = image.format
    except (OSError, UnidentifiedImageError) as error:
        return f"invalid PNG {path}: {error}"
    if image_format != "PNG":
        return f"expected PNG format at {path}, got {image_format}"
    if exact_size and size != (CANVAS_WIDTH, CANVAS_HEIGHT):
        return f"expected 1080x1350 at {path}, got {size[0]}x{size[1]}"
    if not exact_size and (size[0] < 1024 or size[1] < 1024):
        return f"raw panel is below 1024px at {path}: {size[0]}x{size[1]}"
    return None


def _check_images(
    episode_dir: Path, delivery_config: DeliveryConfig | None
) -> tuple[str, ...]:
    if delivery_config is None:
        return ()
    panel_count, output_layout = delivery_config
    issues: list[str] = []
    raw_paths = tuple(
        episode_dir / "raw" / f"panel-{number}.png"
        for number in range(1, panel_count + 1)
    )
    paths = delivery_paths(episode_dir, panel_count, output_layout)
    final_paths = paths.rendered_panels + paths.final_images
    for path in raw_paths:
        if path.is_file() and (issue := _image_issue(path, exact_size=True)):
            issues.append(issue)
    for path in final_paths:
        if path.is_file() and (issue := _image_issue(path, exact_size=True)):
            issues.append(issue)
    return tuple(issues)


def _check_prompts(
    episode_dir: Path, delivery_config: DeliveryConfig | None
) -> tuple[str, ...]:
    if delivery_config is None:
        return ()
    panel_count, _ = delivery_config
    issues: list[str] = []
    try:
        script = EpisodeScriptModel.model_validate_json((episode_dir / "script.json").read_text(encoding="utf-8"))
    except (OSError, ValidationError) as error:
        return (f"invalid script for prompt validation: {error}",)
    for number in range(1, panel_count + 1):
        path = episode_dir / "prompts" / f"panel-{number}.json"
        if not path.is_file():
            continue
        try:
            prompt = PromptManifestModel.model_validate_json(
                path.read_text(encoding="utf-8")
            )
        except (OSError, ValidationError) as error:
            issues.append(f"invalid prompt manifest {path}: {error}")
            continue
        if prompt.panel != number:
            issues.append(
                f"prompt panel mismatch at {path}: expected {number}, got {prompt.panel}"
            )
        if prompt.size != (CANVAS_WIDTH, CANVAS_HEIGHT):
            issues.append(f"prompt size mismatch at {path}: {prompt.size}")
        if not prompt.negative_prompt.strip():
            issues.append(f"negative prompt is empty at {path}")
        if prompt.information_card != script.panels[number - 1].information_card:
            issues.append(f"information card/presenter prompt metadata is stale at {path}")
    return tuple(issues)


def _check_layout(
    episode_dir: Path, delivery_config: DeliveryConfig | None
) -> tuple[str, ...]:
    if delivery_config is None:
        return ()
    _, output_layout = delivery_config
    path = episode_dir / "final" / "composition.json"
    if not path.is_file():
        return ()
    try:
        manifest = CompositionModel.model_validate_json(
            path.read_text(encoding="utf-8")
        )
    except (OSError, ValidationError) as error:
        return (f"invalid composition manifest {path}: {error}",)
    issues: list[str] = []
    if manifest.canvas != (CANVAS_WIDTH, CANVAS_HEIGHT):
        issues.append(f"composition canvas mismatch: {manifest.canvas}")
    if manifest.output_layout != output_layout:
        issues.append("composition output_layout does not match script output_layout")
    try:
        script = EpisodeScriptModel.model_validate_json((episode_dir / "script.json").read_text(encoding="utf-8"))
    except (OSError, ValidationError) as error:
        return (f"invalid script for composition validation: {error}",)
    scales: dict[int, float] = {}
    next_number = 1
    for group_size in script.output_layout or (1,) * len(script.panels):
        for offset in range(group_size):
            scales[next_number + offset] = _panel_scale(group_size, offset)
        next_number += group_size
    for panel in script.panels:
        if not panel.information_card:
            if any(entry.kind == "card" and entry.panel == panel.panel for entry in manifest.layouts):
                issues.append(f"panel {panel.panel} has unexpected information card text")
            continue
        card = panel.information_card
        entries = [entry for entry in manifest.layouts if entry.panel == panel.panel]
        expected = {("bubble", index): text for index, text in enumerate(panel.dialogue, start=1)}
        expected.update({("card", index): text for index, text in enumerate(card.texts, start=1)})
        keys = [(entry.kind, entry.bubble) for entry in entries]
        if len(keys) != len(set(keys)) or set(keys) != set(expected):
            issues.append(f"panel {panel.panel} composition is missing or duplicating card/dialogue text")
        for index, entry in enumerate(entries):
            source = expected.get((entry.kind, entry.bubble))
            if source is not None:
                if "".join("".join(entry.lines).split()) != "".join(source.text.split()):
                    issues.append(f"panel {panel.panel} {entry.kind} rendered text differs from script")
                geometry = {key: getattr(source, key) for key in ("x", "y", "width", "height")}
                if entry.safe_area.model_dump() != geometry:
                    issues.append(f"panel {panel.panel} {entry.kind} safe area differs from script")
                if entry.kind == "card" and entry.element_id != source.id:
                    issues.append(f"panel {panel.panel} card text ID differs from script")
            if round(entry.font_size * scales[panel.panel]) < MIN_EFFECTIVE_FONT_SIZE:
                issues.append(f"panel {panel.panel} {entry.kind} effective font is below 34px")
            if boxes_overlap(entry.box, card.presenter.area) or any(boxes_overlap(entry.box, other.box) for other in entries[index + 1:]):
                issues.append(f"panel {panel.panel} card/dialogue/presenter overlap")
    for layout in manifest.layouts:
        box = layout.box
        safe = layout.safe_area
        inside_safe = (
            safe.x <= box.x
            and safe.y <= box.y
            and box.x + box.width <= safe.x + safe.width
            and box.y + box.height <= safe.y + safe.height
        )
        if not inside_safe:
            issues.append(
                f"panel {layout.panel} bubble {layout.bubble} exceeds its safe area"
            )
    return tuple(issues)


def validate_episode(episode_dir: Path) -> tuple[Path, tuple[str, ...]]:
    delivery_config = _delivery_config(episode_dir)
    needs_topic_research = requires_topic_research(episode_dir)
    needs_instagram_link_analysis = requires_instagram_link_analysis(episode_dir)
    missing = tuple(
        f"missing required file: {path}"
        for path in _required_paths(
            episode_dir,
            delivery_config,
            needs_topic_research,
            needs_instagram_link_analysis,
        )
        if not path.is_file()
    )
    issues = (
        missing
        + _check_models(episode_dir)
        + content_review_issues(episode_dir)
        + content_lock_issues(episode_dir)
        + layout_preflight_issues(episode_dir)
        + _check_brief_script_layout(episode_dir)
        + hard_banned_issues(episode_dir)
        + language_policy_issues(episode_dir)
        + topic_research_issues(episode_dir)
        + instagram_link_issues(episode_dir)
        + story_module_issues(episode_dir)
        + _check_prompts(episode_dir, delivery_config)
        + _check_images(episode_dir, delivery_config)
        + _check_layout(episode_dir, delivery_config)
    )
    advisory_findings = review_required_findings(episode_dir)
    report_path = episode_dir / "qa-report.md"
    write_text_atomic(
        report_path,
        qa_report_text(
            issues,
            existing_agent_section(report_path),
            QaSupplemental(
                advisory_findings=advisory_findings,
                story_modules=story_module_summary(episode_dir),
            ),
        ),
    )
    return report_path, issues


def main(
    episode_dir: Annotated[
        Path,
        typer.Option("--episode-dir", exists=True, file_okay=False, resolve_path=True),
    ],
) -> None:
    report_path, issues = validate_episode(episode_dir)
    if issues:
        typer.echo(
            "validation failed:\n" + "\n".join(f"- {issue}" for issue in issues),
            err=True,
        )
        raise typer.Exit(code=1)
    typer.echo(f"validated episode: {report_path}")


if __name__ == "__main__":
    typer.run(main)
