from __future__ import annotations

from datetime import datetime
from typing import Annotated, ClassVar, Literal, Self

from pydantic import ConfigDict, Field, HttpUrl, model_validator
from pydantic_core import PydanticCustomError

from episode_models import (
    HumorEngineId,
    NonBlankString,
    PRIMARY_HUMOR_ENGINE_IDS,
    StrictModel,
)


ResearchSourceMode = Literal["public_web", "local_fallback"]
ResearchSourceKind = Literal["public_page", "official_trend"]


class TopicScoreModel(StrictModel):
    relatability: Annotated[int, Field(ge=0, le=30)]
    humor: Annotated[int, Field(ge=0, le=30)]
    opening_hook: Annotated[int, Field(ge=0, le=20)]
    novelty: Annotated[int, Field(ge=0, le=10)]
    production_fit: Annotated[int, Field(ge=0, le=10)]
    total: Annotated[int, Field(ge=0, le=100)]

    @model_validator(mode="after")
    def total_matches_dimensions(self) -> Self:
        dimension_total = (
            self.relatability
            + self.humor
            + self.opening_hook
            + self.novelty
            + self.production_fit
        )
        if self.total != dimension_total:
            raise PydanticCustomError(
                "topic_score_total", "topic score total must equal its dimensions"
            )
        return self


class PublicEngagementModel(StrictModel):
    """Public response counts observed on a normally accessible source page."""

    likes: Annotated[int, Field(ge=0)] | None = None
    comments: Annotated[int, Field(ge=0)] | None = None
    reactions: Annotated[int, Field(ge=0)] | None = None
    upvotes: Annotated[int, Field(ge=0)] | None = None

    @model_validator(mode="after")
    def contains_visible_metric(self) -> Self:
        if all(
            metric is None
            for metric in (self.likes, self.comments, self.reactions, self.upvotes)
        ):
            raise PydanticCustomError(
                "public_engagement",
                "public engagement requires at least one visible metric",
            )
        return self


class TopicSourceModel(StrictModel):
    id: str
    kind: ResearchSourceKind
    url: HttpUrl
    title: str
    observation: str
    accessed_at: datetime
    engagement: PublicEngagementModel | None = None


class TopicCandidateModel(StrictModel):
    id: str
    topic: str
    observation: str
    story_seed: str
    source_ids: tuple[str, ...]
    engagement_priority: Annotated[int, Field(ge=0, le=100)] = 0
    scores: TopicScoreModel


class EditorialGateResultsModel(StrictModel):
    model_config: ClassVar[ConfigDict] = ConfigDict(
        frozen=True, extra="forbid", strict=True
    )

    source_relevance: bool
    human_observation: bool
    behavioral_contradiction: bool
    humor_engine: bool
    hook_seed: bool
    payoff_seed: bool
    safety: bool
    duplicate: bool

    def passed(self) -> bool:
        return all(self.model_dump().values())


class StoryQualityTopicCandidateModel(StrictModel):
    id: str
    topic: str
    observation: str
    story_seed: str
    source_ids: tuple[str, ...]
    engagement_priority: Annotated[int, Field(ge=0, le=100)] = 0
    source_signal: NonBlankString
    source_relevance: NonBlankString
    human_observation: NonBlankString
    behavioral_contradiction: NonBlankString
    humor_engine_id: HumorEngineId
    engine_explanation: NonBlankString
    hook_seed: NonBlankString
    payoff_seed: NonBlankString
    beat_signature: NonBlankString
    eligibility: bool
    gate_results: EditorialGateResultsModel
    scores: TopicScoreModel

    @model_validator(mode="after")
    def eligibility_matches_gate_results(self) -> Self:
        if self.eligibility != self.gate_results.passed():
            raise PydanticCustomError(
                "topic_eligibility", "eligibility must match editorial gate results"
            )
        return self

    @model_validator(mode="after")
    def other_engine_has_meaningful_explanation(self) -> Self:
        if self.humor_engine_id == "other" and not self.engine_explanation.strip():
            raise PydanticCustomError(
                "topic_engine_explanation",
                "the other humor engine requires a non-blank explanation",
            )
        return self


RichTopicCandidateModel = StoryQualityTopicCandidateModel


class TopicResearchModel(StrictModel):
    schema_version: Literal["1.0", "1.1"]
    source_mode: ResearchSourceMode
    search_window_days: Annotated[int, Field(ge=1, le=90)]
    sources: tuple[TopicSourceModel, ...]
    candidates: Annotated[
        tuple[TopicCandidateModel | RichTopicCandidateModel, ...],
        Field(min_length=5, max_length=5),
    ]
    selected_candidate_id: str
    selected_topic: str
    selection_reason: str
    fallback_reason: Annotated[str, Field(min_length=1)] | None = None

    @model_validator(mode="after")
    def selected_candidate_passes_editorial_gate(self) -> Self:
        if self.schema_version == "1.0":
            if not all(isinstance(candidate, TopicCandidateModel) for candidate in self.candidates):
                raise PydanticCustomError(
                    "topic_candidates",
                    "topic research schema 1.0 only accepts legacy candidates",
                )
        elif not all(
            isinstance(candidate, RichTopicCandidateModel)
            for candidate in self.candidates
        ):
            raise PydanticCustomError(
                "topic_candidates",
                "topic research schema 1.1 requires story-quality candidates",
            )
        if self.schema_version == "1.1":
            primary_engines = {
                candidate.humor_engine_id
                for candidate in self.candidates
                if isinstance(candidate, StoryQualityTopicCandidateModel)
                and candidate.humor_engine_id in PRIMARY_HUMOR_ENGINE_IDS
            }
            if len(primary_engines) < 3:
                raise PydanticCustomError(
                    "topic_humor_engines",
                    "topic research schema 1.1 requires at least three distinct primary humor engines",
                )
        candidate_ids = tuple(candidate.id for candidate in self.candidates)
        if len(set(candidate_ids)) != len(candidate_ids):
            raise PydanticCustomError(
                "topic_candidate_ids", "topic candidate ids must be unique"
            )
        selected = next(
            (
                candidate
                for candidate in self.candidates
                if candidate.id == self.selected_candidate_id
            ),
            None,
        )
        if selected is None:
            raise PydanticCustomError(
                "topic_selection", "selected candidate id must name a candidate"
            )
        if selected.topic != self.selected_topic:
            raise PydanticCustomError(
                "topic_selection", "selected topic must match the selected candidate"
            )
        if self.schema_version == "1.1":
            match selected:
                case StoryQualityTopicCandidateModel() as story_quality_selected:
                    if not story_quality_selected.eligibility:
                        raise PydanticCustomError(
                            "topic_selection", "selected candidate must be eligible"
                        )
                case TopicCandidateModel():
                    raise PydanticCustomError(
                        "topic_candidates",
                        "topic research schema 1.1 requires story-quality candidates",
                    )
        eligible_candidates = (
            tuple(
                candidate
                for candidate in self.candidates
                if isinstance(candidate, StoryQualityTopicCandidateModel)
                and candidate.eligibility
            )
            if self.schema_version == "1.1"
            else self.candidates
        )
        if not eligible_candidates:
            raise PydanticCustomError(
                "topic_selection", "topic research requires an eligible candidate"
            )
        if self._selection_key(selected) != max(
            self._selection_key(candidate) for candidate in eligible_candidates
        ):
            raise PydanticCustomError(
                "topic_selection",
                "selected candidate must have the highest eligible engagement priority, then total",
            )
        if self.schema_version == "1.1" and (
            selected.scores.total < 75
            or selected.scores.relatability < 18
            or selected.scores.humor < 18
            or selected.scores.opening_hook < 12
        ):
            raise PydanticCustomError(
                "topic_selection", "selected candidate does not meet editorial thresholds"
            )
        match self.source_mode:
            case "public_web":
                self._validate_public_sources(selected)
            case "local_fallback":
                self._validate_local_fallback()
        return self

    @staticmethod
    def _selection_key(
        candidate: TopicCandidateModel | RichTopicCandidateModel,
    ) -> tuple[int, int]:
        return candidate.engagement_priority, candidate.scores.total

    def _validate_public_sources(
        self, selected: TopicCandidateModel | RichTopicCandidateModel
    ) -> None:
        if self.fallback_reason is not None:
            raise PydanticCustomError(
                "topic_fallback", "public web research cannot include a fallback reason"
            )
        source_ids = tuple(source.id for source in self.sources)
        if len(set(source_ids)) != len(source_ids):
            raise PydanticCustomError("topic_sources", "topic source ids must be unique")
        known_source_ids = set(source_ids)
        sources_by_id = {source.id: source for source in self.sources}
        for candidate in self.candidates:
            if not candidate.source_ids:
                raise PydanticCustomError(
                    "topic_sources", "public-web candidates require source ids"
                )
            if not set(candidate.source_ids).issubset(known_source_ids):
                raise PydanticCustomError(
                    "topic_sources", "candidate source ids must name known sources"
                )
            if candidate.engagement_priority > 0 and not any(
                sources_by_id[source_id].engagement is not None
                for source_id in candidate.source_ids
            ):
                raise PydanticCustomError(
                    "topic_engagement",
                    "engagement priority requires a cited source with visible public engagement",
                )
        selected_sources = tuple(
            source for source in self.sources if source.id in selected.source_ids
        )
        has_official_trend = False
        for source in selected_sources:
            match source.kind:
                case "official_trend":
                    has_official_trend = True
                case "public_page":
                    continue
        if len(selected_sources) < 2 and not has_official_trend:
            raise PydanticCustomError(
                "topic_sources",
                "selected public-web topic needs two sources or one official trend source",
            )

    def _validate_local_fallback(self) -> None:
        if self.sources:
            raise PydanticCustomError(
                "topic_fallback", "local fallback cannot include public web sources"
            )
        if self.fallback_reason is None:
            raise PydanticCustomError(
                "topic_fallback", "local fallback requires a fallback reason"
            )
        if any(candidate.source_ids for candidate in self.candidates):
            raise PydanticCustomError(
                "topic_fallback", "local fallback candidates cannot cite web sources"
            )
        if any(candidate.engagement_priority for candidate in self.candidates):
            raise PydanticCustomError(
                "topic_fallback",
                "local fallback candidates cannot claim public engagement priority",
            )
