from __future__ import annotations

from typing import Annotated, Literal, Self, assert_never

from pydantic import Field, model_validator
from pydantic_core import PydanticCustomError

from story_choice_models import (
    Beat as Beat,
    BriefModel as BriefModel,
    CANVAS_HEIGHT as CANVAS_HEIGHT,
    CANVAS_WIDTH as CANVAS_WIDTH,
    CanvasSize as CanvasSize,
    DirectionModel as DirectionModel,
    DuplicateCheckModel as DuplicateCheckModel,
    HumorEngineId as HumorEngineId,
    NonBlankString as NonBlankString,
    PRIMARY_HUMOR_ENGINE_IDS as PRIMARY_HUMOR_ENGINE_IDS,
    RenderMode as RenderMode,
    RichDirectionModel as RichDirectionModel,
    Section as Section,
    SensitivityCheckModel as SensitivityCheckModel,
    StoryQualityDirectionModel as StoryQualityDirectionModel,
    StrictModel as StrictModel,
    TopicOrigin as TopicOrigin,
)


class BoxModel(StrictModel):
    x: Annotated[int, Field(ge=0)]
    y: Annotated[int, Field(ge=0)]
    width: Annotated[int, Field(gt=0)]
    height: Annotated[int, Field(gt=0)]

    @model_validator(mode="after")
    def inside_canvas(self) -> Self:
        if self.x + self.width > CANVAS_WIDTH or self.y + self.height > CANVAS_HEIGHT:
            raise PydanticCustomError(
                "bubble_bounds", "bubble safe area exceeds the 1080x1350 canvas"
            )
        return self


class DialogueModel(BoxModel):
    speaker: str
    text: Annotated[str, Field(min_length=1)]


class WardrobeOverrideModel(StrictModel):
    character_id: NonBlankString
    outfit: NonBlankString
    footwear: NonBlankString
    story_reason: NonBlankString


class PanelModel(StrictModel):
    panel: Annotated[int, Field(ge=1)]
    section: Section | None = None
    beat: Beat
    scene: str
    expression: str
    action: str
    props: tuple[str, ...]
    background: str
    camera: str
    wardrobe_overrides: tuple[WardrobeOverrideModel, ...] = ()
    dialogue: Annotated[tuple[DialogueModel, ...], Field(max_length=2)]

    @model_validator(mode="after")
    def unique_wardrobe_overrides(self) -> Self:
        character_ids = tuple(
            override.character_id for override in self.wardrobe_overrides
        )
        if len(character_ids) != len(set(character_ids)):
            raise PydanticCustomError(
                "wardrobe_overrides",
                "each panel may define only one wardrobe override per character",
            )
        return self


class EpisodeScriptModel(StrictModel):
    schema_version: Literal["1.0", "1.1"]
    episode_id: str
    title: str
    panels: Annotated[tuple[PanelModel, ...], Field(min_length=3)]
    output_layout: Annotated[
        tuple[Annotated[int, Field(ge=1, le=4)], ...], Field(min_length=1)
    ] | None = None

    @model_validator(mode="after")
    def ordered_panels(self) -> Self:
        match self.schema_version:
            case "1.0":
                return self._validate_legacy_panels()
            case "1.1":
                return self._validate_layout_panels()
            case unreachable:
                assert_never(unreachable)

    def _validate_legacy_panels(self) -> Self:
        panel_count = len(self.panels)
        if self.output_layout is not None:
            raise PydanticCustomError(
                "output_layout", "legacy scripts must not define output_layout"
            )
        if panel_count not in (4, 6):
            raise PydanticCustomError(
                "panel_count", "legacy scripts must contain either 4 or 6 panels"
            )
        expected_numbers = tuple(range(1, panel_count + 1))
        if tuple(panel.panel for panel in self.panels) != expected_numbers:
            raise PydanticCustomError(
                "panel_order", "panels must be numbered consecutively from 1"
            )
        if panel_count == 4:
            expected_beats = ("setup", "escalation", "tension", "twist")
            if tuple(panel.beat for panel in self.panels) != expected_beats:
                raise PydanticCustomError(
                    "panel_beats",
                    "legacy panel beats must be setup, escalation, tension, twist",
                )
            return self
        expected_sections = (
            "opening",
            "development",
            "development",
            "development",
            "development",
            "ending",
        )
        if tuple(panel.section for panel in self.panels) != expected_sections:
            raise PydanticCustomError(
                "panel_sections",
                "six-panel sections must be opening, four development panels, ending",
            )
        expected_beats = (
            "opening_hook",
            "development_setup",
            "development_escalation",
            "development_complication",
            "development_turn",
            "ending_payoff",
        )
        if tuple(panel.beat for panel in self.panels) != expected_beats:
            raise PydanticCustomError(
                "panel_beats",
                "six-panel beats must be opening hook, four development beats, ending payoff",
            )
        return self

    def _validate_layout_panels(self) -> Self:
        if self.output_layout is None:
            raise PydanticCustomError(
                "output_layout", "schema 1.1 scripts require output_layout"
            )
        panel_count = len(self.panels)
        if sum(self.output_layout) != panel_count:
            raise PydanticCustomError(
                "output_layout", "output_layout must account for every panel exactly once"
            )
        expected_numbers = tuple(range(1, panel_count + 1))
        if tuple(panel.panel for panel in self.panels) != expected_numbers:
            raise PydanticCustomError(
                "panel_order", "panels must be numbered consecutively from 1"
            )
        expected_sections = (
            ("opening",) + ("development",) * (panel_count - 2) + ("ending",)
        )
        if tuple(panel.section for panel in self.panels) != expected_sections:
            raise PydanticCustomError(
                "panel_sections",
                "layout scripts must have opening, development panels, then ending",
            )
        expected_beats = (
            ("opening_hook",)
            + ("development",) * (panel_count - 2)
            + ("ending_payoff",)
        )
        if tuple(panel.beat for panel in self.panels) != expected_beats:
            raise PydanticCustomError(
                "panel_beats",
                "layout scripts must have opening hook, development beats, then ending payoff",
            )
        return self


class ContinuityModel(StrictModel):
    previous_panel: int | None
    locked_characters: tuple[str, ...]
    locked_props: tuple[str, ...]


class PromptManifestModel(StrictModel):
    schema_version: Literal["1.0"]
    panel: Annotated[int, Field(ge=1)]
    revision: Annotated[int, Field(ge=0)]
    mode: RenderMode
    size: CanvasSize
    prompt: str
    negative_prompt: str
    reference_images: tuple[str, ...]
    bubble_safe_areas: tuple[BoxModel, ...]
    continuity: ContinuityModel


class LayoutEntryModel(StrictModel):
    panel: Annotated[int, Field(ge=1)]
    bubble: Annotated[int, Field(ge=1, le=2)]
    box: BoxModel
    safe_area: BoxModel
    font_size: Annotated[int, Field(ge=26)]
    lines: Annotated[tuple[str, ...], Field(min_length=1)]


class CompositionModel(StrictModel):
    schema_version: Literal["1.0", "1.1"]
    canvas: CanvasSize
    layouts: tuple[LayoutEntryModel, ...]
    output_layout: tuple[Annotated[int, Field(ge=1, le=4)], ...] | None = None

    @model_validator(mode="after")
    def validate_output_layout(self) -> Self:
        match self.schema_version:
            case "1.0" if self.output_layout is None:
                return self
            case "1.0":
                raise PydanticCustomError(
                    "output_layout", "legacy compositions must not define output_layout"
                )
            case "1.1" if self.output_layout is not None:
                return self
            case "1.1":
                raise PydanticCustomError(
                    "output_layout", "schema 1.1 compositions require output_layout"
                )
            case unreachable:
                assert_never(unreachable)
