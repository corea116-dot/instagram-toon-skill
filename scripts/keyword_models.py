from __future__ import annotations

from datetime import date, datetime
from typing import Annotated, Literal, Self

from episode_models import PRIMARY_HUMOR_ENGINE_IDS, NonBlankString, StrictModel
from pydantic import AwareDatetime, ConfigDict, Field, HttpUrl, TypeAdapter, model_validator
from pydantic_core import PydanticCustomError
from topic_research_models import RichTopicCandidateModel

KeywordType = Literal["trending", "evergreen"]
Platform = Literal["naver", "google"]
Method = Literal["monthly_volume", "relative_index", "related_rank"]


class KeywordSource(StrictModel):
    id: NonBlankString
    kind: Literal["naver", "google", "official"]
    url: HttpUrl
    title: NonBlankString
    observation: NonBlankString
    accessed_at: datetime


class KeywordCandidate(RichTopicCandidateModel):
    keyword: NonBlankString
    category: Literal[
        "government_support", "personal_finance", "economy", "stocks", "real_estate"
    ]
    keyword_type: KeywordType
    demand_reason: NonBlankString
    official_source_ids: Annotated[tuple[str, ...], Field(min_length=1)]
    event_kind: Literal["announcement", "deadline"] | None = None
    event_date: date | None = None

    @model_validator(mode="after")
    def event_is_paired(self) -> Self:
        if (self.event_kind is None) != (self.event_date is None):
            raise PydanticCustomError(
                "keyword_event", "event kind and official date must be paired"
            )
        return self


class InformationalKeywordGates(StrictModel):
    model_config = ConfigDict(frozen=True, extra="forbid", strict=True)

    audience_fit: bool
    source_relevance: bool
    safety: bool
    duplicate: bool

    def passed(self) -> bool:
        return all(self.model_dump().values())


class InformationalKeywordCandidate(StrictModel):
    id: NonBlankString
    topic: NonBlankString
    keyword: NonBlankString
    category: Literal[
        "government_support", "personal_finance", "economy", "stocks", "real_estate"
    ]
    keyword_type: KeywordType
    demand_reason: NonBlankString
    reader_question: NonBlankString
    audience_fit: NonBlankString
    source_relevance: NonBlankString
    safety_note: NonBlankString
    duplicate_note: NonBlankString
    source_ids: Annotated[tuple[NonBlankString, ...], Field(min_length=1)]
    official_source_ids: Annotated[tuple[NonBlankString, ...], Field(min_length=1)]
    eligibility: bool
    gate_results: InformationalKeywordGates
    event_kind: Literal["announcement", "deadline"] | None = None
    event_date: date | None = None

    @model_validator(mode="after")
    def valid_candidate(self) -> Self:
        if self.eligibility != self.gate_results.passed():
            raise PydanticCustomError(
                "keyword_eligibility", "eligibility must match informational gate results"
            )
        if (self.event_kind is None) != (self.event_date is None):
            raise PydanticCustomError(
                "keyword_event", "event kind and official date must be paired"
            )
        return self


class SearchValue(StrictModel):
    candidate_id: NonBlankString
    value: Annotated[float, Field(ge=0, allow_inf_nan=False)]
    source_id: NonBlankString
    previous_value: Annotated[float, Field(ge=0, allow_inf_nan=False)] | None = None
    pc_searches: Annotated[int, Field(ge=0, strict=True)] | None = None
    mobile_searches: Annotated[int, Field(ge=0, strict=True)] | None = None


class SearchBatch(StrictModel):
    platform: Platform
    method: Method
    comparison_key: NonBlankString
    window_start: date | None = None
    window_end: date | None = None
    reporting_period: NonBlankString | None = None
    observed_at: AwareDatetime | None = None
    geo: Literal["KR"]
    previous_window_start: date | None = None
    previous_window_end: date | None = None
    values: Annotated[tuple[SearchValue, ...], Field(min_length=1, max_length=5)]

    @model_validator(mode="after")
    def comparable_values(self) -> Self:
        if (self.window_start is None) != (self.window_end is None):
            raise PydanticCustomError("keyword_window", "provide both dates or neither")
        if self.window_start is None:
            if self.platform != "naver" or self.method != "monthly_volume" or self.reporting_period is None or self.observed_at is None:
                raise PydanticCustomError("keyword_window", "undated Naver monthly counts require provider reporting_period and observed_at")
        elif self.window_start > self.window_end:
            raise PydanticCustomError("keyword_window", "invalid measurement window")
        if len({item.candidate_id for item in self.values}) != len(self.values):
            raise PydanticCustomError(
                "keyword_values", "duplicate candidate in comparison batch"
            )
        for item in self.values:
            for value in (item.value, item.previous_value):
                if value is None:
                    continue
                if self.method == "monthly_volume" and not value.is_integer():
                    raise PydanticCustomError(
                        "keyword_volume", "exact monthly volume must be an integer"
                    )
                if self.method == "relative_index" and value > 100:
                    raise PydanticCustomError(
                        "keyword_index", "relative index must be between 0 and 100"
                    )
                if self.method == "related_rank" and (
                    value < 1 or not value.is_integer()
                ):
                    raise PydanticCustomError(
                        "keyword_rank", "related rank must be a positive integer"
                    )
        previous = self.previous_window_start, self.previous_window_end
        if any(value is not None for value in previous) or any(
            item.previous_value is not None for item in self.values
        ):
            if self.window_start is None:
                raise PydanticCustomError("keyword_previous", "growth comparison requires explicit measurement dates")
            start, end = previous
            if start is None or end is None or not start <= end < self.window_start:
                raise PydanticCustomError(
                    "keyword_previous",
                    "previous values require an earlier comparison window",
                )
            if end - start != self.window_end - self.window_start:
                raise PydanticCustomError(
                    "keyword_previous", "growth windows must have equal duration"
                )
        return self


class KeywordEvidence(StrictModel):
    schema_version: Literal["1.0"]
    # Missing on historical records: retain their original reproducible calculation.
    selection_policy: Literal["legacy_weighted", "naver_monthly"] = "legacy_weighted"
    researched_on: date
    sources: tuple[KeywordSource, ...]
    candidates: Annotated[
        tuple[KeywordCandidate, ...], Field(min_length=5, max_length=5)
    ]
    batches: tuple[SearchBatch, ...]
    collection_notes: NonBlankString

    @model_validator(mode="after")
    def source_integrity(self) -> Self:
        candidates = {item.id for item in self.candidates}
        sources = {item.id: item for item in self.sources}
        if len(candidates) != 5 or len({item.keyword for item in self.candidates}) != 5:
            raise PydanticCustomError(
                "keyword_ids", "five distinct candidates and keywords are required"
            )
        if len(sources) != len(self.sources):
            raise PydanticCustomError("keyword_sources", "source ids must be unique")
        if self.schema_version == "1.0":
            engines = {item.humor_engine_id for item in self.candidates} & set(
                PRIMARY_HUMOR_ENGINE_IDS
            )
            if len(engines) < 3:
                raise PydanticCustomError(
                    "keyword_engines", "at least three primary humor engines are required"
                )
        for source in self.sources:
            if (
                source.accessed_at.tzinfo is None
                or not 0 <= (self.researched_on - source.accessed_at.date()).days <= 7
            ):
                raise PydanticCustomError(
                    "keyword_freshness",
                    "sources must be observed within seven days, with timezone",
                )
        for candidate in self.candidates:
            if (
                not candidate.source_ids
                or not set(candidate.source_ids) <= sources.keys()
            ):
                raise PydanticCustomError(
                    "keyword_sources", "candidate source references are missing"
                )
            if any(
                key not in sources or sources[key].kind != "official"
                for key in candidate.official_source_ids
            ):
                raise PydanticCustomError(
                    "keyword_official",
                    "official facts need an official source reference",
                )
        for batch in self.batches:
            if self.selection_policy == "naver_monthly" and batch.platform == "naver" and batch.method == "monthly_volume":
                for item in batch.values:
                    if item.pc_searches is None or item.mobile_searches is None or item.value != item.pc_searches + item.mobile_searches:
                        raise PydanticCustomError(
                            "keyword_components", "Naver monthly volume requires observed PC + mobile components matching the total"
                        )
            if batch.window_end is not None and not 0 <= (self.researched_on - batch.window_end).days <= 62:
                raise PydanticCustomError(
                    "keyword_freshness",
                    "search windows must end within the last 62 days",
                )
            if batch.observed_at is not None and not 0 <= (self.researched_on - batch.observed_at.date()).days <= 7:
                raise PydanticCustomError("keyword_freshness", "batch observation must be within seven days")
            for item in batch.values:
                if item.candidate_id not in candidates or item.source_id not in sources:
                    raise PydanticCustomError(
                        "keyword_values",
                        "measurement references an unknown candidate or source",
                    )
                if sources[item.source_id].kind != batch.platform:
                    raise PydanticCustomError(
                        "keyword_platform",
                        "measurement source belongs to another platform",
                    )
                if batch.window_end is None and sources[item.source_id].accessed_at.date() != batch.observed_at.date():
                    raise PydanticCustomError("keyword_window", "undated monthly values must share the observation date")
        return self


class InformationalKeywordEvidence(KeywordEvidence):
    schema_version: Literal["1.1"]
    content_type: Literal["informational"]
    candidates: Annotated[
        tuple[InformationalKeywordCandidate, ...], Field(min_length=5, max_length=5)
    ]


KeywordEvidenceDocument = Annotated[
    KeywordEvidence | InformationalKeywordEvidence, Field(discriminator="schema_version")
]
keyword_evidence_adapter = TypeAdapter(KeywordEvidenceDocument)


class PlatformBasis(StrictModel):
    platform: Platform
    method: Method
    batch_index: int


class KeywordScore(StrictModel):
    candidate_id: str
    naver: float | None
    google: float | None
    total: float | None
    rank: int | None = None
    rejection_reason: str | None


class KeywordDecision(StrictModel):
    status: Literal["selected", "hold"]
    requested_type: KeywordType
    effective_type: KeywordType | None
    selected_id: str | None
    reason: NonBlankString
    evidence_label: Literal["exact_monthly", "relative_proxy", "insufficient"]
    bases: tuple[PlatformBasis, ...]
    scores: tuple[KeywordScore, ...]


class KeywordResearch(StrictModel):
    schema_version: Literal["1.2"] = "1.2"
    evidence: KeywordEvidence
    decision: KeywordDecision

    @model_validator(mode="after")
    def decision_is_reproducible(self) -> Self:
        from keyword_selection import select_topic

        if self.decision != select_topic(self.evidence, self.decision.requested_type):
            raise PydanticCustomError(
                "keyword_decision", "decision must match recomputed evidence ranking"
            )
        return self

    @property
    def selected_topic(self) -> str | None:
        return next(
            (
                item.topic
                for item in self.evidence.candidates
                if item.id == self.decision.selected_id
            ),
            None,
        )


class InformationalKeywordResearch(KeywordResearch):
    schema_version: Literal["1.3"] = "1.3"
    content_type: Literal["informational"] = "informational"
    evidence: InformationalKeywordEvidence


KeywordResearchDocument = Annotated[
    KeywordResearch | InformationalKeywordResearch, Field(discriminator="schema_version")
]
keyword_research_adapter = TypeAdapter(KeywordResearchDocument)
