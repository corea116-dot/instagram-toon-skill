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


def boxes_overlap(first: BoxModel, second: BoxModel) -> bool:
    return (first.x < second.x + second.width and second.x < first.x + first.width
            and first.y < second.y + second.height and second.y < first.y + first.height)


def box_contains(outer: BoxModel, inner: BoxModel) -> bool:
    return (outer.x <= inner.x and outer.y <= inner.y
            and inner.x + inner.width <= outer.x + outer.width
            and inner.y + inner.height <= outer.y + outer.height)


class CardTextModel(BoxModel):
    id: NonBlankString
    text: NonBlankString
    color: Annotated[str, Field(pattern=r"^#[0-9a-fA-F]{6}$")] = "#1b1f26"
    align: Literal["left", "center", "right"] = "left"


class CardShapeModel(BoxModel):
    shape: Literal["rectangle", "rounded_rectangle", "ellipse"] = "rectangle"
    fill: Annotated[str, Field(pattern=r"^#[0-9a-fA-F]{6}$")] = "#ffffff"


class CardPresenterModel(StrictModel):
    character_id: NonBlankString
    area: BoxModel
    pose: NonBlankString
    explanation_bubble: Annotated[int, Field(ge=1, le=2)]


class InformationCardModel(StrictModel):
    format: NonBlankString
    design_reason: NonBlankString
    area: BoxModel
    texts: Annotated[tuple[CardTextModel, ...], Field(min_length=1)]
    shapes: tuple[CardShapeModel, ...] = ()
    presenter: CardPresenterModel

    @model_validator(mode="after")
    def card_geometry(self) -> Self:
        if len({text.id for text in self.texts}) != len(self.texts):
            raise ValueError("information card text IDs must be unique")
        if any(not box_contains(self.area, item) for item in (*self.texts, *self.shapes)):
            raise ValueError("information card texts and shapes must stay inside card area")
        for index, text in enumerate(self.texts):
            if any(boxes_overlap(text, other) for other in self.texts[index + 1:]):
                raise ValueError("information card text regions must not overlap")
        if boxes_overlap(self.area, self.presenter.area):
            raise ValueError("information card must not overlap presenter area")
        return self


class WardrobeOverrideModel(StrictModel):
    character_id: NonBlankString
    outfit: NonBlankString
    footwear: NonBlankString
    story_reason: NonBlankString


class PanelModel(StrictModel):
    panel: Annotated[int, Field(ge=1)]
    section: Section | None = None
    beat: Beat
    panel_job: NonBlankString | None = None
    new_information: NonBlankString | None = None
    reader_takeaway: NonBlankString | None = None
    scope: NonBlankString | None = None
    text_budget: Annotated[int, Field(ge=12, le=180)] | None = None
    scene: str
    expression: str
    action: str
    props: tuple[str, ...]
    background: str
    camera: str
    wardrobe_overrides: tuple[WardrobeOverrideModel, ...] = ()
    dialogue: Annotated[tuple[DialogueModel, ...], Field(max_length=2)]
    information_card: InformationCardModel | None = None

    @model_validator(mode="after")
    def unique_wardrobe_overrides(self) -> Self:
        if self.information_card is not None:
            card = self.information_card
            index = card.presenter.explanation_bubble - 1
            if index >= len(self.dialogue):
                raise ValueError("information card requires a same-panel explanation bubble")
            explanation = self.dialogue[index]
            if (explanation.speaker != card.presenter.character_id
                    or not explanation.text.strip()):
                raise ValueError("information card explanation must be spoken by its presenter")
            for index, dialogue in enumerate(self.dialogue):
                if boxes_overlap(card.area, dialogue) or boxes_overlap(card.presenter.area, dialogue):
                    raise ValueError("information card, presenter and dialogue areas must not overlap")
                if any(boxes_overlap(dialogue, other) for other in self.dialogue[index + 1:]):
                    raise ValueError("information card dialogue areas must not overlap")
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
    schema_version: Literal["1.0", "1.1", "1.2"]
    episode_id: str
    title: str
    panels: Annotated[tuple[PanelModel, ...], Field(min_length=3)]
    output_layout: (
        Annotated[tuple[Annotated[int, Field(ge=1, le=4)], ...], Field(min_length=1)]
        | None
    ) = None

    @model_validator(mode="after")
    def ordered_panels(self) -> Self:
        if self.schema_version != "1.2" and any(panel.information_card for panel in self.panels):
            raise ValueError("information cards require informational script schema 1.2")
        match self.schema_version:
            case "1.0":
                return self._validate_legacy_panels()
            case "1.1":
                return self._validate_layout_panels()
            case "1.2":
                _ = self._validate_layout_panels()
                return self._validate_informational_panels()
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
                "output_layout",
                "output_layout must account for every panel exactly once",
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

    def _validate_informational_panels(self) -> Self:
        required_fields = (
            "panel_job",
            "new_information",
            "reader_takeaway",
            "scope",
            "text_budget",
        )
        for panel in self.panels:
            missing = tuple(
                field for field in required_fields if getattr(panel, field) is None
            )
            if missing:
                raise PydanticCustomError(
                    "informational_panel_contract",
                    "panel {panel} is missing: {missing}",
                    {"panel": panel.panel, "missing": ", ".join(missing)},
                )
            assert panel.text_budget is not None
            visible_characters = sum(
                len("".join(dialogue.text.split())) for dialogue in panel.dialogue
            )
            if panel.information_card:
                visible_characters += sum(len("".join(text.text.split())) for text in panel.information_card.texts)
            if visible_characters > panel.text_budget:
                raise PydanticCustomError(
                    "informational_text_budget",
                    "panel {panel} has {actual} visible characters; budget is {budget}",
                    {
                        "panel": panel.panel,
                        "actual": visible_characters,
                        "budget": panel.text_budget,
                    },
                )
        for previous, current in zip(self.panels, self.panels[1:], strict=False):
            assert previous.panel_job is not None and current.panel_job is not None
            if (
                previous.panel_job.strip().casefold()
                == current.panel_job.strip().casefold()
            ):
                raise PydanticCustomError(
                    "informational_panel_job",
                    "adjacent panels {previous} and {current} must have different panel_job values",
                    {"previous": previous.panel, "current": current.panel},
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
    information_card: InformationCardModel | None = None


class LayoutEntryModel(StrictModel):
    panel: Annotated[int, Field(ge=1)]
    bubble: Annotated[int, Field(ge=1)]
    kind: Literal["bubble", "card"] = "bubble"
    element_id: NonBlankString | None = None
    box: BoxModel
    safe_area: BoxModel
    font_size: Annotated[int, Field(ge=26)]
    lines: Annotated[tuple[str, ...], Field(min_length=1)]

    @model_validator(mode="after")
    def text_identity(self) -> Self:
        if self.kind == "bubble" and (self.bubble > 2 or self.element_id is not None):
            raise ValueError("bubble layout requires index 1 or 2 and no element_id")
        if self.kind == "card" and self.element_id is None:
            raise ValueError("card layout requires element_id")
        return self


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
