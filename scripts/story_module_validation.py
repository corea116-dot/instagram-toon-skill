from __future__ import annotations

from pathlib import Path

from pydantic import ValidationError

from episode_models import BriefModel
from story_module_models import StoryModuleRoutingModel


def requires_story_module_routing(episode_dir: Path) -> bool:
    brief_path = episode_dir / "brief.json"
    if not brief_path.is_file():
        return False
    try:
        brief = BriefModel.model_validate_json(brief_path.read_text(encoding="utf-8"))
    except (OSError, ValidationError):
        return False
    return brief.story_module_policy == "auto_with_overrides"


def _read_routing(episode_dir: Path) -> StoryModuleRoutingModel | None:
    path = episode_dir / "module-routing.json"
    if not path.is_file():
        return None
    return StoryModuleRoutingModel.model_validate_json(path.read_text(encoding="utf-8"))


def story_module_issues(episode_dir: Path) -> tuple[str, ...]:
    path = episode_dir / "module-routing.json"
    if not path.is_file():
        return (
            (f"missing required file: {path}",)
            if requires_story_module_routing(episode_dir)
            else ()
        )
    try:
        _ = _read_routing(episode_dir)
    except (OSError, ValidationError) as error:
        return (f"invalid structured file {path}: {error}",)
    return ()


def story_module_summary(episode_dir: Path) -> tuple[str, ...]:
    try:
        routing = _read_routing(episode_dir)
    except (OSError, ValidationError):
        return ()
    if routing is None:
        return ()
    active = tuple(
        f"{module.id.value} ({module.reason}, runs={module.runs})"
        for module in routing.modules
        if module.status == "active"
    )
    skipped = tuple(
        f"{module.id.value} ({module.reason})"
        for module in routing.modules
        if module.status == "skipped"
    )
    budget_summary = ", ".join(
        (
            f"optional={routing.budget.max_optional_modules}",
            f"branch={routing.budget.max_branch_rounds}",
            "rewrites="
            + f"{routing.budget.script_rewrites_used}/"
            + f"{routing.budget.max_script_rewrites}",
        )
    )
    return (
        f"policy: {routing.policy}",
        f"mode: {routing.mode.value}",
        "active: " + (", ".join(active) if active else "none"),
        "skipped: " + (", ".join(skipped) if skipped else "none"),
        f"budget: {budget_summary}",
    )
