from __future__ import annotations

from pathlib import Path
from typing import assert_never

from episode_models import BriefModel
from keyword_history import ResearchVersion
from keyword_models import keyword_research_adapter
from pydantic import ValidationError
from topic_research_models import TopicResearchModel


def requires_topic_research(episode_dir: Path) -> bool:
    path = episode_dir / "brief.json"
    if not path.is_file():
        return False
    try:
        brief = BriefModel.model_validate_json(path.read_text(encoding="utf-8"))
    except (OSError, ValidationError):
        return False
    match brief.topic_origin:
        case "editorial_scout":
            return True
        case "user" | "instagram_link":
            return False
        case _ as unreachable:
            assert_never(unreachable)


def topic_research_issues(episode_dir: Path) -> tuple[str, ...]:
    brief_path = episode_dir / "brief.json"
    if not brief_path.is_file():
        return ()
    try:
        brief = BriefModel.model_validate_json(brief_path.read_text(encoding="utf-8"))
    except (OSError, ValidationError):
        return ()
    match brief.topic_origin:
        case "user" | "instagram_link":
            return ()
        case "editorial_scout":
            pass
        case _ as unreachable:
            assert_never(unreachable)
    if brief.schema_version not in ("1.1", "1.2", "1.3"):
        return (
            f"editorial_scout episodes require brief schema 1.1, 1.2 or 1.3: {brief_path}",
        )
    path = episode_dir / "topic-research.json"
    if not path.is_file():
        return ()
    try:
        raw = path.read_text(encoding="utf-8")
        if ResearchVersion.model_validate_json(raw).schema_version in ("1.2", "1.3"):
            keyword_research = keyword_research_adapter.validate_json(raw)
            if (
                keyword_research.schema_version == "1.3"
                and brief.content_type != "informational"
            ):
                return (
                    f"informational topic research requires an informational brief: {path}",
                )
            if keyword_research.decision.status != "selected":
                return (f"held keyword research cannot proceed to an episode: {path}",)
            if brief.topic != keyword_research.selected_topic:
                return (
                    f"topic-research selected topic does not match brief topic: {path}",
                )
            return ()
        research = TopicResearchModel.model_validate_json(raw)
    except (OSError, ValidationError) as error:
        return (f"invalid structured file {path}: {error}",)
    if research.schema_version != "1.1":
        return (f"editorial_scout episodes require topic research schema 1.1: {path}",)
    if brief.topic == research.selected_topic:
        return ()
    return (f"topic-research selected topic does not match brief topic: {path}",)
