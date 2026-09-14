from __future__ import annotations

from typing import Annotated, ClassVar, Literal, Self, assert_never

from pydantic import BaseModel, ConfigDict, Field, StringConstraints, model_validator
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
    development_changes: Annotated[
        tuple[NonBlankString, ...], Field(min_length=1)
    ]
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


class BriefModel(StrictModel):
    schema_version: Literal["1.0", "1.1"]
    episode_id: str
    title: str
    topic: str
    topic_origin: TopicOrigin = "user"
    audience: str
    tone: str
    characters: tuple[str, ...]
    directions: Annotated[
        tuple[DirectionModel | RichDirectionModel, ...],
        Field(min_length=3, max_length=3),
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
        if self.schema_version == "1.0":
            if self.output_layout is not None:
                raise PydanticCustomError(
                    "output_layout", "brief schema 1.0 must not define output_layout"
                )
            if not all(isinstance(direction, DirectionModel) for direction in self.directions):
                raise PydanticCustomError(
                    "brief_directions",
                    "brief schema 1.0 only accepts legacy directions",
                )
            return self
        if not all(
            isinstance(direction, RichDirectionModel)
            for direction in self.directions
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
            (direction for direction in self.directions if direction.id == self.selected_direction),
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
            case DirectionModel():
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
