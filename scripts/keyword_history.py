from __future__ import annotations

from hashlib import sha256
from pathlib import Path
from typing import Annotated, Literal

from episode_models import StrictModel
from keyword_models import KeywordType, keyword_research_adapter
from pydantic import BaseModel, ConfigDict, Field
from pydantic_core import PydanticCustomError


class KeywordCompletion(StrictModel):
    requested_type: KeywordType
    effective_type: KeywordType
    review_state: Literal["review_pending"] = "review_pending"
    research_sha256: Annotated[str, Field(pattern=r"^[a-f0-9]{64}$")]


class ReviewState(StrictModel):
    status: Literal["review_pending"]
    topic_research_sha256: Annotated[str, Field(pattern=r"^[a-f0-9]{64}$")]
    story_qa: Literal["PASS"]
    dialogue_qa: Literal["PASS"]
    continuity_qa: Literal["PASS"]
    visual_qa: Literal["PASS"]


class InformationalReviewState(StrictModel):
    status: Literal["review_pending"]
    topic_research_sha256: Annotated[str, Field(pattern=r"^[a-f0-9]{64}$")]
    content_review: Literal["PASS"]
    visual_qa: Literal["PASS"]


class ResearchVersion(BaseModel):
    model_config = ConfigDict(frozen=True)
    schema_version: str


class _Entry(BaseModel):
    model_config = ConfigDict(frozen=True)
    episode_id: str
    keyword_selection: KeywordCompletion | None = None


class _History(BaseModel):
    model_config = ConfigDict(frozen=True)
    episodes: tuple[_Entry, ...]


def next_keyword_type(history_path: Path) -> KeywordType:
    history = _History.model_validate_json(history_path.read_text(encoding="utf-8"))
    completed = {
        entry.episode_id
        for entry in history.episodes
        if entry.keyword_selection is not None
    }
    return "evergreen" if len(completed) % 2 else "trending"


def completion_for_episode(
    episode_dir: Path, topic_origin: str
) -> KeywordCompletion | None:
    if topic_origin != "editorial_scout":
        return None
    research_path = episode_dir / "topic-research.json"
    raw = research_path.read_bytes()
    if ResearchVersion.model_validate_json(raw).schema_version not in ("1.2", "1.3"):
        return None
    research = keyword_research_adapter.validate_json(raw)
    if (
        research.decision.status != "selected"
        or research.decision.effective_type is None
    ):
        raise PydanticCustomError(
            "keyword_completion", "held topic research cannot advance rotation"
        )
    from episode_models import BriefModel

    brief = BriefModel.model_validate_json((episode_dir / "brief.json").read_bytes())
    informational = getattr(brief, "content_type", None) == "informational"
    if informational:
        from content_review import require_content_review

        require_content_review(episode_dir)
    review_model = InformationalReviewState if informational else ReviewState
    review = review_model.model_validate_json(
        (episode_dir / "review-state.json").read_bytes()
    )
    digest = sha256(raw).hexdigest()
    if review.topic_research_sha256 != digest:
        raise PydanticCustomError(
            "keyword_completion", "review state does not match topic research"
        )
    from validate_episode import validate_episode

    _, issues = validate_episode(episode_dir)
    if issues:
        raise PydanticCustomError(
            "keyword_completion",
            "episode validation failed: {issues}",
            {"issues": "; ".join(issues)},
        )
    return KeywordCompletion(
        requested_type=research.decision.requested_type,
        effective_type=research.decision.effective_type,
        research_sha256=digest,
    )
