"""Compact discovery and explicit editorial judgment; no popularity forecasts."""
from __future__ import annotations

import unicodedata
from datetime import date
from typing import Annotated, Literal, Self

from episode_models import NonBlankString, StrictModel
from pydantic import Field, model_validator

Domain = Literal['government_support', 'salary_consumption', 'investment', 'housing']


def keyword_key(value: str) -> str:
    return ''.join(unicodedata.normalize('NFKC', value).split()).casefold()


class EditorialRating(StrictModel):
    value: Annotated[int, Field(ge=0, le=2, strict=True)]
    reason: NonBlankString


class EditorialDirection(StrictModel):
    reader_situation: NonBlankString
    opening_question: NonBlankString
    answer_action: NonBlankString
    save_share_use: NonBlankString
    reader_relevance: EditorialRating
    episode_clarity: EditorialRating
    practical_value: EditorialRating
    judgment_kind: Literal['ai_editorial_judgment']

    @property
    def total(self) -> int:
        return sum(x.value for x in (self.reader_relevance, self.episode_clarity, self.practical_value))


class DiscoveryCandidate(StrictModel):
    id: NonBlankString
    keyword: NonBlankString
    domain: Domain
    source_kind: Literal['official', 'observed_related_keyword', 'prior_candidate', 'supplied_comment', 'supplied_performance']
    source_reference: NonBlankString
    observed_on: date
    audience_relevance: NonBlankString
    shortlist: bool
    decision_reason: NonBlankString


class DiscoveryPool(StrictModel):
    schema_version: Literal['1.0'] = '1.0'
    researched_on: date
    candidates: Annotated[tuple[DiscoveryCandidate, ...], Field(min_length=1, max_length=15)]
    # One short observation per territory, including an honest no-evidence result.
    coverage: dict[Domain, NonBlankString]
    diversity_exception: NonBlankString | None = None

    @model_validator(mode='after')
    def integrity(self) -> Self:
        if len({c.id for c in self.candidates}) != len(self.candidates):
            raise ValueError('discovery IDs must be unique')
        if any(c.observed_on > self.researched_on for c in self.candidates):
            raise ValueError('discovery observations cannot be future-dated')
        if set(self.coverage) != {'government_support', 'salary_consumption', 'investment', 'housing'}:
            raise ValueError('record coverage or absence for all four territories')
        return self

    def normalized(self) -> dict:
        """Keep every observation; duplicate groups select at most one representative."""
        grouped: dict[str, list[DiscoveryCandidate]] = {}
        for item in self.candidates:
            grouped.setdefault(keyword_key(item.keyword), []).append(item)
        kept = []
        duplicates = []
        for group in grouped.values():
            selected = [c for c in group if c.shortlist]
            if len(selected) > 1:
                raise ValueError('duplicate keyword has multiple shortlisted representatives')
            representative = selected[0] if selected else group[0]
            kept.append(representative)
            duplicates.extend({'id': c.id, 'representative_id': representative.id} for c in group if c.id != representative.id)
        shortlist = [c for c in kept if c.shortlist]
        reasons = []
        if len(shortlist) != 5:
            reasons.append('exactly five distinct shortlisted candidates required')
        if len({c.domain for c in shortlist}) < 3 and not self.diversity_exception:
            reasons.append('fewer than three shortlisted territories requires an explicit exception')
        return {'status': 'ready' if not reasons else 'hold', 'reasons': reasons,
                'shortlisted_ids': [c.id for c in shortlist], 'duplicates': duplicates,
                'unique_candidate_count': len(kept), 'pool': self.model_dump(mode='json')}
