from __future__ import annotations

from enum import StrEnum, unique
from typing import Annotated, ClassVar, Final, Literal, Self, assert_never

from pydantic import BaseModel, ConfigDict, Field, StringConstraints, model_validator
from pydantic_core import PydanticCustomError


NonBlankString = Annotated[str, StringConstraints(strip_whitespace=True, min_length=1)]


@unique
class StoryModuleId(StrEnum):
    STORY_ARCHITECTURE = "story-architecture"
    CONTINUITY_CANON = "continuity-canon"
    DIALOGUE_PERSONA = "dialogue-persona"
    BRANCH_PAYOFF_LAB = "branch-payoff-lab"
    STORYBOARD_SHOT_PLAN = "storyboard-shot-plan"


@unique
class StoryModuleStatus(StrEnum):
    ACTIVE = "active"
    SKIPPED = "skipped"


@unique
class RoutingMode(StrEnum):
    NEW_EPISODE = "new_episode"
    STORY_REWRITE = "story_rewrite"
    PANEL_REGENERATION = "panel_regeneration"
    RECOMPOSE = "recompose"
    VALIDATE = "validate"


@unique
class StoryFailureClass(StrEnum):
    TOPIC = "topic"
    MECHANISM = "mechanism"
    HOOK = "hook"
    BEATS = "beats"
    PAYOFF = "payoff"
    DIALOGUE = "dialogue"
    DUPLICATE = "duplicate"
    SAFETY = "safety"
    VISUAL = "visual"


ALL_STORY_MODULE_IDS: Final = tuple(StoryModuleId)
OPTIONAL_MODULE_IDS: Final = frozenset(
    (StoryModuleId.CONTINUITY_CANON, StoryModuleId.DIALOGUE_PERSONA)
)
BRANCH_FAILURE_CLASSES: Final = frozenset(
    (
        StoryFailureClass.MECHANISM,
        StoryFailureClass.BEATS,
        StoryFailureClass.PAYOFF,
        StoryFailureClass.DUPLICATE,
    )
)


class StrictModel(BaseModel):
    model_config: ClassVar[ConfigDict] = ConfigDict(extra="forbid", frozen=True)


class StoryModuleOverrideModel(StrictModel):
    enable: tuple[StoryModuleId, ...] = ()
    disable: tuple[StoryModuleId, ...] = ()

    @model_validator(mode="after")
    def override_lists_are_unique(self) -> Self:
        if len(set(self.enable)) != len(self.enable):
            raise PydanticCustomError(
                "story_module_override",
                "enabled story module IDs must be unique",
            )
        if len(set(self.disable)) != len(self.disable):
            raise PydanticCustomError(
                "story_module_override",
                "disabled story module IDs must be unique",
            )
        return self


class StoryModuleBudgetModel(StrictModel):
    max_optional_modules: Literal[2] = 2
    max_branch_rounds: Literal[1] = 1
    max_script_rewrites: Literal[2] = 2
    script_rewrites_used: Annotated[int, Field(ge=0, le=2)] = 0


class StoryModuleEntryModel(StrictModel):
    id: StoryModuleId
    status: StoryModuleStatus
    reason: NonBlankString
    runs: Annotated[int, Field(ge=0, le=1)]

    @model_validator(mode="after")
    def status_matches_runs(self) -> Self:
        match self.status:
            case StoryModuleStatus.ACTIVE:
                expected_runs = 1
            case StoryModuleStatus.SKIPPED:
                expected_runs = 0
            case unreachable:
                assert_never(unreachable)
        if self.runs != expected_runs:
            raise PydanticCustomError(
                "story_module_runs",
                "story module status and run count must agree",
            )
        return self


class StoryModuleRoutingModel(StrictModel):
    schema_version: Literal["1.0"] = "1.0"
    policy: Literal["auto_with_overrides"] = "auto_with_overrides"
    mode: RoutingMode
    overrides: StoryModuleOverrideModel = StoryModuleOverrideModel()
    modules: Annotated[
        tuple[StoryModuleEntryModel, ...], Field(min_length=5, max_length=5)
    ]
    budget: StoryModuleBudgetModel = StoryModuleBudgetModel()

    @model_validator(mode="after")
    def complete_registry_stays_within_budget(self) -> Self:
        module_ids = tuple(module.id for module in self.modules)
        if len(set(module_ids)) != len(module_ids):
            raise PydanticCustomError(
                "story_module_registry",
                "story module entries must be unique",
            )
        if frozenset(module_ids) != frozenset(ALL_STORY_MODULE_IDS):
            raise PydanticCustomError(
                "story_module_registry",
                "routing must record every known story module exactly once",
            )
        optional_runs = sum(
            module.runs for module in self.modules if module.id in OPTIONAL_MODULE_IDS
        )
        if optional_runs > self.budget.max_optional_modules:
            raise PydanticCustomError(
                "story_module_budget",
                "optional story module budget exceeded",
            )
        branch_runs = next(
            module.runs
            for module in self.modules
            if module.id is StoryModuleId.BRANCH_PAYOFF_LAB
        )
        if branch_runs > self.budget.max_branch_rounds:
            raise PydanticCustomError(
                "story_module_budget",
                "branch-payoff-lab round budget exceeded",
            )
        return self


class RoutingSignalsModel(StrictModel):
    mode: RoutingMode
    overrides: StoryModuleOverrideModel = StoryModuleOverrideModel()
    speaker_count: Annotated[int, Field(ge=0)] = 0
    serial_signal: bool = False
    story_changed: bool = True
    failure_class: StoryFailureClass | None = None
    script_rewrites_used: Annotated[int, Field(ge=0, le=2)] = 0


def _mode_allows_story_modules(signals: RoutingSignalsModel) -> bool:
    match signals.mode:
        case RoutingMode.NEW_EPISODE | RoutingMode.STORY_REWRITE:
            return True
        case RoutingMode.PANEL_REGENERATION:
            return signals.story_changed
        case RoutingMode.RECOMPOSE | RoutingMode.VALIDATE:
            return False
        case unreachable:
            assert_never(unreachable)


def _automatic_reason(
    module_id: StoryModuleId, signals: RoutingSignalsModel
) -> str | None:
    match module_id:
        case StoryModuleId.STORY_ARCHITECTURE:
            return (
                signals.mode.value
                if signals.mode in (RoutingMode.NEW_EPISODE, RoutingMode.STORY_REWRITE)
                else None
            )
        case StoryModuleId.CONTINUITY_CANON:
            return "serial_signal" if signals.serial_signal else None
        case StoryModuleId.DIALOGUE_PERSONA:
            return "multi_speaker" if signals.speaker_count >= 2 else None
        case StoryModuleId.BRANCH_PAYOFF_LAB:
            failure_class = signals.failure_class
            return (
                f"story_critic_{failure_class.value}"
                if failure_class is not None
                and failure_class in BRANCH_FAILURE_CLASSES
                else None
            )
        case StoryModuleId.STORYBOARD_SHOT_PLAN:
            match signals.mode:
                case RoutingMode.NEW_EPISODE:
                    return "new_episode"
                case RoutingMode.STORY_REWRITE | RoutingMode.PANEL_REGENERATION:
                    return "story_changed" if signals.story_changed else None
                case RoutingMode.RECOMPOSE | RoutingMode.VALIDATE:
                    return None
                case unreachable:
                    assert_never(unreachable)
        case unreachable:
            assert_never(unreachable)


def route_story_modules(signals: RoutingSignalsModel) -> StoryModuleRoutingModel:
    allows_story_modules = _mode_allows_story_modules(signals)
    entries: list[StoryModuleEntryModel] = []
    for module_id in ALL_STORY_MODULE_IDS:
        automatic_reason = _automatic_reason(module_id, signals)
        if not allows_story_modules:
            is_active = False
            reason = "mode_has_no_story_work"
        elif module_id in signals.overrides.disable:
            is_active = False
            reason = "user_disabled"
        elif module_id in signals.overrides.enable:
            is_active = True
            reason = "user_enabled"
        elif automatic_reason is not None:
            is_active = True
            reason = automatic_reason
        else:
            is_active = False
            reason = "no_signal"
        entries.append(
            StoryModuleEntryModel(
                id=module_id,
                status=(
                    StoryModuleStatus.ACTIVE
                    if is_active
                    else StoryModuleStatus.SKIPPED
                ),
                reason=reason,
                runs=int(is_active),
            )
        )
    return StoryModuleRoutingModel(
        mode=signals.mode,
        overrides=signals.overrides,
        modules=tuple(entries),
        budget=StoryModuleBudgetModel(
            script_rewrites_used=signals.script_rewrites_used
        ),
    )
