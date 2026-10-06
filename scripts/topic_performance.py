"""Supplied local insights only. Advisory summaries never alter selection weights."""
from __future__ import annotations

import hashlib
import json
from datetime import timedelta
from typing import Annotated, Literal, Self

from episode_models import NonBlankString, StrictModel
from pydantic import AwareDatetime, Field, model_validator
from topic_editorial import Domain

Count = Annotated[int, Field(ge=0, strict=True)]
METRICS = ('views', 'reach', 'nonfollower_reach', 'follows', 'shares', 'saves')


class PostInsight(StrictModel):
    post_id: NonBlankString
    source_reference: NonBlankString
    published_at: AwareDatetime
    window_end: AwareDatetime
    collected_at: AwareDatetime
    paid: Annotated[bool, Field(strict=True)] | None
    domain: Domain
    story_approach: NonBlankString
    views: Count | None = None
    reach: Count | None = None
    nonfollower_reach: Count | None = None
    follows: Count | None = None
    shares: Count | None = None
    saves: Count | None = None
    missing_reasons: dict[str, NonBlankString]

    @model_validator(mode='after')
    def consistent(self) -> Self:
        if not self.published_at < self.window_end <= self.collected_at:
            raise ValueError('require published_at < window_end <= collected_at')
        missing = {m for m in METRICS if getattr(self, m) is None}
        if self.paid is None:
            missing.add('paid')
        if set(self.missing_reasons) != missing:
            raise ValueError('missing_reasons must explain exactly the missing metrics/paid status')
        if self.reach is not None and self.nonfollower_reach is not None and self.nonfollower_reach > self.reach:
            raise ValueError('nonfollower reach cannot exceed total reach')
        if self.reach == 0 and any((getattr(self, m) or 0) > 0 for m in ('nonfollower_reach', 'follows', 'shares', 'saves')):
            raise ValueError('positive reached-account activity is inconsistent with zero reach')
        return self


class PerformanceInput(StrictModel):
    schema_version: Literal['1.0'] = '1.0'
    posts: tuple[PostInsight, ...]

    @model_validator(mode='after')
    def unique_posts(self) -> Self:
        if len({p.post_id for p in self.posts}) != len(self.posts):
            raise ValueError('one observation per post; replace the observation in the supplied input')
        return self


def summarize_performance(data: PerformanceInput) -> dict:
    digest = hashlib.sha256(data.model_dump_json().encode()).hexdigest()
    groups: dict[tuple, list[PostInsight]] = {}
    excluded = []
    for post in data.posts:
        if post.window_end - post.published_at != timedelta(days=7):
            excluded.append({'post_id': post.post_id, 'reason': 'not an exact seven-day observation window'})
            continue
        groups.setdefault((post.domain, post.story_approach, post.paid), []).append(post)
    summaries = []
    for (domain, approach, paid), posts in sorted(groups.items(), key=lambda pair: json.dumps(pair[0])):
        metrics = {}
        for metric in METRICS:
            observed = [p for p in posts if getattr(p, metric) is not None]
            paired = [p for p in observed if p.reach is not None and p.reach > 0]
            numerator = sum(getattr(p, metric) for p in paired)
            denominator = sum(p.reach for p in paired)
            metrics[metric] = {
                'observed_total': sum(getattr(p, metric) for p in observed) if observed else None,
                'observed_posts': len(observed),
                'missing_posts': len(posts) - len(observed),
                'per_1000_reach': round(1000 * numerator / denominator, 4) if denominator else None,
                'rate_posts': len(paired),
                'rate_reach': denominator if paired else None,
            }
        summaries.append({'domain': domain, 'story_approach': approach, 'paid': paid,
                          'post_count': len(posts), 'post_ids': [p.post_id for p in posts],
                          'metrics': metrics})
    return {'schema_version': '1.0', 'input_sha256': digest, 'window_days': 7,
            'use': 'advisory_only', 'automatic_weights': False,
            'primary_metrics': ['views', 'nonfollower_reach', 'follows'],
            'auxiliary_metrics': ['shares', 'saves'], 'groups': summaries,
            'excluded_observations': excluded,
            'limitations': ['No causal or success-probability claim; display sample counts.',
                            'Unknown, absent and small-sample topics receive no ranking penalty.',
                            'Keep paid, organic and unknown-paid groups separate.']}
