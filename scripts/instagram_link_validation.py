from __future__ import annotations

from pathlib import Path
from typing import assert_never

from pydantic import ValidationError

from episode_models import BriefModel
from instagram_link_models import InstagramLinkAnalysisModel


def requires_instagram_link_analysis(episode_dir: Path) -> bool:
    """Return whether this episode must persist an Instagram source analysis."""
    brief_path = episode_dir / "brief.json"
    if not brief_path.is_file():
        return False
    try:
        brief = BriefModel.model_validate_json(brief_path.read_text(encoding="utf-8"))
    except (OSError, ValidationError):
        return False
    match brief.topic_origin:
        case "instagram_link":
            return True
        case "user" | "editorial_scout":
            return False
        case _ as unreachable:
            assert_never(unreachable)


def instagram_link_issues(episode_dir: Path) -> tuple[str, ...]:
    """Validate source provenance for a completed Instagram-link episode."""
    brief_path = episode_dir / "brief.json"
    if not brief_path.is_file():
        return ()
    try:
        brief = BriefModel.model_validate_json(brief_path.read_text(encoding="utf-8"))
    except (OSError, ValidationError):
        return ()
    match brief.topic_origin:
        case "user" | "editorial_scout":
            return ()
        case "instagram_link":
            pass
        case _ as unreachable:
            assert_never(unreachable)
    if brief.schema_version != "1.1":
        return (f"instagram_link episodes require brief schema 1.1: {brief_path}",)
    analysis_path = episode_dir / "instagram-source.json"
    if not analysis_path.is_file():
        return ()
    try:
        analysis = InstagramLinkAnalysisModel.model_validate_json(
            analysis_path.read_text(encoding="utf-8")
        )
    except (OSError, ValidationError) as error:
        return (f"invalid structured file {analysis_path}: {error}",)
    if brief.topic != analysis.derived_topic:
        return (
            f"instagram-source derived topic does not match brief topic: {analysis_path}",
        )
    return ()
