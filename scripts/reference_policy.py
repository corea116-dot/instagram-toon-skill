from __future__ import annotations

import json
from dataclasses import dataclass
from pathlib import Path

from episode_models import BriefModel, NonBlankString, PanelModel, StrictModel
from pydantic import Field, ValidationError, model_validator
from pydantic_core import PydanticCustomError
from rendering import RenderError

IMAGE_SUFFIXES = frozenset({".png", ".jpg", ".jpeg", ".webp"})
ACTIVE_REFERENCE_MARKER = "assets/references/styles"
ACTIVE_REFERENCE_DIRECTORIES = (
    "assets/references/styles",
    "assets/references/current",
)


class CharacterIdentityModel(StrictModel):
    age_range: NonBlankString
    face: NonBlankString
    hair: NonBlankString
    body: NonBlankString
    immutable_traits: tuple[NonBlankString, ...] = ()


class WardrobeModel(StrictModel):
    default: NonBlankString
    footwear_default: NonBlankString
    story_override_allowed: bool
    work: NonBlankString | None = None
    colors: tuple[NonBlankString, ...] = ()


class CharacterVoiceModel(StrictModel):
    voice_register: NonBlankString = Field(alias="register")
    traits: tuple[NonBlankString, ...]
    avoid: tuple[NonBlankString, ...]


class CharacterModel(StrictModel):
    id: NonBlankString
    display_name: NonBlankString
    role: NonBlankString
    identity: CharacterIdentityModel
    wardrobe: WardrobeModel
    signature_props: tuple[NonBlankString, ...]
    voice: CharacterVoiceModel
    reference_images: tuple[NonBlankString, ...]


class CharacterBibleModel(StrictModel):
    schema_version: NonBlankString
    characters: tuple[CharacterModel, ...]

    @model_validator(mode="after")
    def unique_character_ids(self) -> CharacterBibleModel:
        character_ids = tuple(character.id for character in self.characters)
        if len(character_ids) != len(set(character_ids)):
            raise PydanticCustomError(
                "character_ids", "character-bible character ids must be unique"
            )
        return self


@dataclass(frozen=True, slots=True)
class CharacterReferencePolicy:
    character_ids: tuple[str, ...]
    reference_images: tuple[str, ...]
    identity_text: str
    default_wardrobes: dict[str, tuple[str, str]]


def validate_reference_paths(
    references: tuple[str, ...], skill_root: Path, label: str
) -> tuple[str, ...]:
    if not references:
        raise RenderError(f"{label} must contain at least one path")
    if len(references) != len(set(references)):
        raise RenderError(f"{label} must not contain duplicate paths")
    resolved_root = skill_root.resolve()
    for reference in references:
        configured_path = Path(reference)
        if configured_path.is_absolute():
            raise RenderError(f"{label} {reference!r} must be relative to {skill_root}")
        if any(part == ".." for part in configured_path.parts):
            raise RenderError(f"{label} {reference!r} must not contain path traversal")
        try:
            resolved_path = (skill_root / configured_path).resolve()
        except (OSError, RuntimeError) as error:
            raise RenderError(
                f"{label} {reference!r} could not be resolved: {error}"
            ) from error
        if not resolved_path.is_relative_to(resolved_root):
            raise RenderError(f"{label} {reference!r} escapes skill root {skill_root}")
        if not resolved_path.is_file():
            raise RenderError(
                f"{label} {reference!r} is not a regular file under {skill_root}"
            )
    return references


def resolve_reference_paths(
    references: tuple[str, ...], skill_root: Path, label: str
) -> tuple[str, ...]:
    if ACTIVE_REFERENCE_MARKER not in references:
        return validate_reference_paths(references, skill_root, label)

    active_references: tuple[str, ...] = ()
    for directory in ACTIVE_REFERENCE_DIRECTORIES:
        folder = skill_root / directory
        images = (
            [
                path
                for path in folder.iterdir()
                if path.is_file()
                and not path.name.startswith(".")
                and path.suffix.lower() in IMAGE_SUFFIXES
            ]
            if folder.is_dir()
            else []
        )
        if images:
            active_references = tuple(
                f"{directory}/{path.name}"
                for path in sorted(images, key=lambda path: path.name)
            )
            break
    if not active_references:
        raise RenderError(
            f"{label} needs a PNG, JPG, or WebP in assets/references/styles/ or assets/references/current/"
        )

    resolved = tuple(
        path
        for reference in references
        for path in (
            active_references if reference == ACTIVE_REFERENCE_MARKER else (reference,)
        )
    )
    return validate_reference_paths(resolved, skill_root, label)


def load_character_policy(
    episode_dir: Path, character_bible_path: Path, skill_root: Path
) -> CharacterReferencePolicy:
    brief_path = episode_dir / "brief.json"
    try:
        brief = BriefModel.model_validate_json(brief_path.read_text(encoding="utf-8"))
        character_bible = CharacterBibleModel.model_validate_json(
            character_bible_path.read_text(encoding="utf-8")
        )
    except (OSError, ValidationError, json.JSONDecodeError) as error:
        raise RenderError(
            f"invalid character reference configuration for {episode_dir}: {error}"
        ) from error

    if not brief.characters:
        return CharacterReferencePolicy((), (), "", {})
    characters_by_id = {
        character.id: character for character in character_bible.characters
    }
    missing = tuple(
        character_id
        for character_id in brief.characters
        if character_id not in characters_by_id
    )
    if missing:
        raise RenderError(
            f"character-bible at {character_bible_path} has no reference for: {', '.join(missing)}"
        )

    selected = tuple(
        characters_by_id[character_id] for character_id in brief.characters
    )
    references = tuple(
        dict.fromkeys(
            reference
            for character in selected
            for reference in resolve_reference_paths(
                character.reference_images, skill_root, "character references"
            )
        )
    )
    identity_text = " ".join(
        (
            f"{character.display_name}: face={character.identity.face}; "
            f"hair={character.identity.hair}; body={character.identity.body}; "
            f"immutable traits={', '.join(character.identity.immutable_traits)}."
        )
        for character in selected
    )
    wardrobes = {
        character.id: (character.wardrobe.default, character.wardrobe.footwear_default)
        for character in selected
    }
    return CharacterReferencePolicy(
        character_ids=tuple(character.id for character in selected),
        reference_images=references,
        identity_text=identity_text,
        default_wardrobes=wardrobes,
    )


def wardrobe_text_for_panel(
    character_policy: CharacterReferencePolicy,
    panel_number: int,
    script_panels: tuple[PanelModel, ...],
) -> str:
    wardrobe_state = dict(character_policy.default_wardrobes)
    for panel in script_panels:
        if panel.panel > panel_number:
            break
        for override in panel.wardrobe_overrides:
            if override.character_id not in wardrobe_state:
                raise RenderError(
                    f"panel {panel.panel} changes wardrobe for absent character {override.character_id!r}"
                )
            wardrobe_state[override.character_id] = (override.outfit, override.footwear)
    return " ".join(
        f"{character_id}: outfit={outfit}; footwear={footwear}."
        for character_id, (outfit, footwear) in wardrobe_state.items()
    )
