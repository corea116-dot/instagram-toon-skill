from __future__ import annotations

import re
from dataclasses import dataclass
from typing import Annotated, Final, Literal, override
from urllib.parse import urlsplit

from pydantic import Field, model_validator
from pydantic_core import PydanticCustomError

from episode_models import (
    DuplicateCheckModel,
    HumorEngineId,
    NonBlankString,
    SensitivityCheckModel,
    StrictModel,
)


InstagramPostType = Literal["post", "reel"]
InstagramAccessStatus = Literal["public", "requires_user_input"]
InstagramAnalysisOutcome = Literal["pass", "requires_user_input"]
SourceDistanceResult = Literal["pass", "review"]
SourceDimension = Literal[
    "setting",
    "protagonist_goal",
    "escalation_path",
    "props_visual_metaphor",
    "dialogue",
]
_INSTAGRAM_HOSTS: Final = frozenset(
    {"instagram.com", "www.instagram.com", "m.instagram.com"}
)
_SHORTCODE: Final = re.compile(r"^[A-Za-z0-9_-]+$")


@dataclass(frozen=True, slots=True)
class InstagramLinkError(ValueError):
    detail: str

    @override
    def __str__(self) -> str:
        return self.detail


@dataclass(frozen=True, slots=True)
class NormalizedInstagramPost:
    canonical_url: str
    post_type: InstagramPostType


def normalize_instagram_post_url(raw_url: str) -> NormalizedInstagramPost:
    """Parse one direct Instagram post or reel URL into its canonical form."""
    parsed = urlsplit(raw_url)
    if parsed.scheme not in {"http", "https"}:
        raise InstagramLinkError("link must use http or https")
    if parsed.username is not None or parsed.password is not None:
        raise InstagramLinkError("link must not include credentials")
    hostname = (parsed.hostname or "").lower()
    if hostname not in _INSTAGRAM_HOSTS:
        raise InstagramLinkError("link must be an Instagram URL")
    path_segments = tuple(segment for segment in parsed.path.split("/") if segment)
    match path_segments:
        case ("p", shortcode) if _SHORTCODE.fullmatch(shortcode):
            return NormalizedInstagramPost(
                canonical_url=f"https://www.instagram.com/p/{shortcode}/",
                post_type="post",
            )
        case ("reel", shortcode) if _SHORTCODE.fullmatch(shortcode):
            return NormalizedInstagramPost(
                canonical_url=f"https://www.instagram.com/reel/{shortcode}/",
                post_type="reel",
            )
        case _:
            raise InstagramLinkError("link must be a direct Instagram post or reel link")


class SourceDistanceCheckModel(StrictModel):
    result: SourceDistanceResult
    changed_dimensions: Annotated[
        tuple[SourceDimension, ...], Field(min_length=3, max_length=5)
    ]
    ending_reversal_reused: bool = False

    @model_validator(mode="after")
    def requires_three_distinct_changed_dimensions(self) -> SourceDistanceCheckModel:
        if len(set(self.changed_dimensions)) < 3:
            raise PydanticCustomError(
                "instagram_source_distance",
                "instagram link analysis requires three changed story dimensions",
            )
        return self


class InstagramLinkAnalysisModel(StrictModel):
    schema_version: Literal["1.0"]
    source_platform: Literal["instagram"]
    canonical_url: NonBlankString
    post_type: InstagramPostType
    access_status: InstagramAccessStatus
    accessed_at: NonBlankString
    derived_topic: NonBlankString
    human_observation: NonBlankString
    behavioral_contradiction: NonBlankString
    humor_engine_candidates: Annotated[
        tuple[HumorEngineId, ...], Field(min_length=1)
    ]
    hook_pattern: NonBlankString
    payoff_pattern: NonBlankString
    excluded_elements: Annotated[tuple[NonBlankString, ...], Field(min_length=3)]
    source_distance_check: SourceDistanceCheckModel
    duplicate_check: DuplicateCheckModel
    safety_check: SensitivityCheckModel
    outcome: InstagramAnalysisOutcome

    @model_validator(mode="after")
    def canonical_url_matches_post_type(self) -> InstagramLinkAnalysisModel:
        try:
            normalized = normalize_instagram_post_url(self.canonical_url)
        except InstagramLinkError as error:
            raise PydanticCustomError(
                "instagram_source_url", "invalid Instagram source URL: {detail}", {"detail": str(error)}
            ) from error
        if normalized.canonical_url != self.canonical_url:
            raise PydanticCustomError(
                "instagram_source_url",
                "Instagram source URL must be canonical",
            )
        if normalized.post_type != self.post_type:
            raise PydanticCustomError(
                "instagram_source_post_type",
                "Instagram source post type must match canonical URL",
            )
        return self

    @model_validator(mode="after")
    def completed_analysis_requires_all_pass_gates(self) -> InstagramLinkAnalysisModel:
        if self.access_status != "public" or self.outcome != "pass":
            raise PydanticCustomError(
                "instagram_source_access",
                "completed Instagram episodes require a public source analysis outcome",
            )
        if self.source_distance_check.result != "pass":
            raise PydanticCustomError(
                "instagram_source_distance",
                "Instagram source distance check must pass before story writing",
            )
        if self.duplicate_check.result != "pass" or self.safety_check.result != "pass":
            raise PydanticCustomError(
                "instagram_source_review",
                "Instagram source duplicate and safety checks must pass",
            )
        return self
