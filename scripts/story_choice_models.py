from __future__ import annotations

from datetime import date
from typing import Annotated, ClassVar, Literal, Self, assert_never

from pydantic import (
    AnyHttpUrl,
    BaseModel,
    ConfigDict,
    Field,
    StringConstraints,
    model_validator,
)
from pydantic_core import PydanticCustomError

CANVAS_WIDTH = 1080
CANVAS_HEIGHT = 1350
CanvasSize = tuple[int, int]
Section = Literal["opening", "development", "ending"]
Beat = Literal[
    "setup",
    "escalation",
    "tension",
    "twist",
    "opening_hook",
    "development",
    "development_setup",
    "development_escalation",
    "development_complication",
    "development_turn",
    "ending_payoff",
]
RenderMode = Literal["mock", "native", "api"]
TopicOrigin = Literal["user", "editorial_scout", "instagram_link"]
HumorEngineId = Literal[
    "semantic_authority_reversal",
    "personified_cognition_action_contradiction",
    "self_rationalization_loop",
    "magnitude_mismatch",
    "repetition_escalation",
    "collective_optimism_reality_collapse",
    "moving_goalpost_paralysis",
    "social_timing_or_role_reversal",
    "other",
]
PRIMARY_HUMOR_ENGINE_IDS = (
    "semantic_authority_reversal",
    "personified_cognition_action_contradiction",
    "self_rationalization_loop",
    "magnitude_mismatch",
    "repetition_escalation",
    "collective_optimism_reality_collapse",
    "moving_goalpost_paralysis",
    "social_timing_or_role_reversal",
)
NonBlankString = Annotated[str, StringConstraints(strip_whitespace=True, min_length=1)]
OutputLayout = Annotated[
    tuple[Annotated[int, Field(ge=1, le=4)], ...], Field(min_length=1)
]


class StrictModel(BaseModel):
    model_config: ClassVar[ConfigDict] = ConfigDict(extra="forbid", frozen=True)


class DirectionModel(StrictModel):
    id: str
    premise: str
    escalation: str
    twist: str
    why_relatable: str


class RichDirectionModel(StrictModel):
    id: str
    premise: str
    human_truth: NonBlankString
    behavioral_contradiction: NonBlankString
    humor_engine_id: HumorEngineId
    engine_explanation: NonBlankString
    hook_promise: NonBlankString
    development_changes: Annotated[tuple[NonBlankString, ...], Field(min_length=1)]
    payoff_reversal: NonBlankString
    beat_signature: NonBlankString
    why_relatable: NonBlankString

    @model_validator(mode="after")
    def development_changes_are_distinct(self) -> Self:
        if len(set(self.development_changes)) != len(self.development_changes):
            raise PydanticCustomError(
                "direction_development_changes",
                "directions require distinct development changes",
            )
        return self

    @model_validator(mode="after")
    def other_engine_has_meaningful_explanation(self) -> Self:
        if self.humor_engine_id == "other" and not self.engine_explanation.strip():
            raise PydanticCustomError(
                "direction_engine_explanation",
                "the other humor engine requires a non-blank explanation",
            )
        return self


StoryQualityDirectionModel = RichDirectionModel


class DuplicateCheckModel(StrictModel):
    matched_episode_ids: tuple[str, ...]
    result: Literal["pass", "review"]


class SensitivityCheckModel(StrictModel):
    issues: tuple[str, ...]
    result: Literal["pass", "review"]


class FactSourceModel(StrictModel):
    url: AnyHttpUrl
    title: NonBlankString
    publisher: NonBlankString
    checked_on: date
    supporting_excerpt: NonBlankString


class RequiredFactModel(StrictModel):
    id: NonBlankString
    claim: NonBlankString
    category: Literal[
        "identity", "relevance", "benefit", "condition", "risk", "uncertainty"
    ]
    sources: Annotated[tuple[FactSourceModel, ...], Field(min_length=1)]


class QuestionAnswerModel(StrictModel):
    search_keyword: NonBlankString
    reader_question: NonBlankString
    one_line_answer: NonBlankString
    required_facts: Annotated[tuple[RequiredFactModel, ...], Field(min_length=1)]
    reader_action: NonBlankString
    reader_actions: Annotated[tuple[NonBlankString, ...], Field(max_length=3)] = ()
    out_of_scope: Annotated[tuple[NonBlankString, ...], Field(min_length=1)]

    @model_validator(mode="after")
    def unique_facts(self) -> Self:
        ids = [fact.id for fact in self.required_facts]
        if len(ids) != len(set(ids)):
            raise ValueError("required_facts must have unique IDs")
        if len(self.reader_actions) != len(set(self.reader_actions)):
            raise ValueError("reader_actions must be distinct")
        return self


class InformationalDirectionModel(StrictModel):
    id: NonBlankString
    premise: NonBlankString
    hook_promise: NonBlankString
    development_changes: Annotated[tuple[NonBlankString, ...], Field(min_length=1)]
    ending_answer: NonBlankString


class BriefModel(StrictModel):
    schema_version: Literal["1.0", "1.1", "1.2", "1.3"]
    content_type: Literal["humor", "informational"] = "humor"
    question_answer: QuestionAnswerModel | None = None
    additional_direction_reason: NonBlankString | None = None
    episode_id: str
    title: str
    topic: str
    topic_origin: TopicOrigin = "user"
    audience: str
    tone: str
    characters: tuple[str, ...]
    directions: Annotated[
        tuple[DirectionModel | RichDirectionModel | InformationalDirectionModel, ...],
        Field(min_length=1, max_length=3),
    ]
    selected_direction: str
    duplicate_check: DuplicateCheckModel
    sensitivity_check: SensitivityCheckModel
    selected_humor_engine_id: str | None = None
    selected_beat_signature: str | None = None
    hook_mode: str | None = None
    output_layout: OutputLayout | None = None
    story_module_policy: Literal["auto_with_overrides"] | None = None
    status: Literal["draft", "approved", "published"] = "draft"

    @model_validator(mode="after")
    def validates_schema_specific_direction_contract(self) -> Self:
        if self.schema_version in ("1.2", "1.3"):
            return self._validate_informational()
        if self.content_type != "humor" or self.question_answer is not None:
            raise ValueError("informational briefs require schema 1.2 or 1.3")
        if len(self.directions) != 3:
            raise ValueError("legacy humor briefs require exactly three directions")
        if self.schema_version == "1.0":
            if self.output_layout is not None:
                raise PydanticCustomError(
                    "output_layout", "brief schema 1.0 must not define output_layout"
                )
            if not all(
                isinstance(direction, DirectionModel) for direction in self.directions
            ):
                raise PydanticCustomError(
                    "brief_directions",
                    "brief schema 1.0 only accepts legacy directions",
                )
            return self
        if not all(
            isinstance(direction, RichDirectionModel) for direction in self.directions
        ):
            raise PydanticCustomError(
                "brief_directions",
                "brief schema 1.1 requires story-quality directions",
            )
        primary_engines = {
            direction.humor_engine_id
            for direction in self.directions
            if isinstance(direction, RichDirectionModel)
            and direction.humor_engine_id in PRIMARY_HUMOR_ENGINE_IDS
        }
        if len(primary_engines) < 2:
            raise PydanticCustomError(
                "brief_humor_engines",
                "brief schema 1.1 requires at least two distinct primary humor engines",
            )
        if self.output_layout is None:
            expected_changes = 4
        else:
            expected_changes = sum(self.output_layout) - 2
        if not all(
            len(direction.development_changes) == expected_changes
            for direction in self.directions
            if isinstance(direction, RichDirectionModel)
        ):
            raise PydanticCustomError(
                "brief_development_changes",
                "directions must have one development change per inner story panel",
            )
        if (
            self.selected_humor_engine_id is None
            or self.selected_beat_signature is None
            or self.hook_mode is None
        ):
            raise PydanticCustomError(
                "brief_story_quality",
                "brief schema 1.1 requires selected story-quality metadata",
            )
        selected = next(
            (
                direction
                for direction in self.directions
                if direction.id == self.selected_direction
            ),
            None,
        )
        if selected is None:
            raise PydanticCustomError(
                "selected_direction", "selected direction must name a direction"
            )
        match selected:
            case StoryQualityDirectionModel() as story_quality_selected:
                selected_engine = story_quality_selected.humor_engine_id
                selected_signature = story_quality_selected.beat_signature
            case DirectionModel() | InformationalDirectionModel():
                raise PydanticCustomError(
                    "brief_directions",
                    "brief schema 1.1 requires story-quality directions",
                )
            case _ as unreachable:
                assert_never(unreachable)
        if selected_engine != self.selected_humor_engine_id:
            raise PydanticCustomError(
                "selected_direction", "selected engine must match selected direction"
            )
        if selected_signature != self.selected_beat_signature:
            raise PydanticCustomError(
                "selected_direction",
                "selected beat signature must match selected direction",
            )
        return self

    def _validate_informational(self) -> Self:
        if self.content_type != "informational" or self.question_answer is None:
            raise ValueError(
                "schema 1.2/1.3 requires informational content and question_answer"
            )
        if self.output_layout is None or sum(self.output_layout) < 3:
            raise ValueError(
                "informational briefs require an output_layout with at least three panels"
            )
        if any(
            value is not None
            for value in (self.selected_humor_engine_id, self.selected_beat_signature)
        ):
            raise ValueError("informational briefs must not use legacy humor metadata")
        if len(self.directions) > 1 and self.additional_direction_reason is None:
            raise ValueError("additional informational directions require a reason")
        if self.schema_version == "1.3" and not self.question_answer.reader_actions:
            raise ValueError(
                "brief schema 1.3 requires one to three concrete reader_actions"
            )
        ids = [direction.id for direction in self.directions]
        if len(ids) != len(set(ids)) or self.selected_direction not in ids:
            raise ValueError("selected_direction must name one unique direction")
        for direction in self.directions:
            if not isinstance(direction, InformationalDirectionModel):
                raise ValueError(
                    "informational briefs require informational directions"
                )
            changes = direction.development_changes
            if len(changes) != sum(self.output_layout) - 2 or len(changes) != len(
                set(changes)
            ):
                raise ValueError(
                    "informational directions require a distinct change per inner panel"
                )
        return self
