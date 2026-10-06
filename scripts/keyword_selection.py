from __future__ import annotations

from keyword_models import (
    InformationalKeywordCandidate,
    KeywordCandidate,
    KeywordDecision,
    KeywordEvidence,
    KeywordScore,
    KeywordType,
    Method,
    Platform,
    PlatformBasis,
    SearchBatch,
)

METHODS: tuple[Method, ...] = ("monthly_volume", "relative_index", "related_rank")
PLATFORMS: tuple[Platform, ...] = ("naver", "google")


def _basis(evidence: KeywordEvidence, platform: Platform) -> PlatformBasis | None:
    methods = ("monthly_volume",) if evidence.selection_policy in ("naver_monthly", "editorial_v1") and platform == "naver" else METHODS
    for method in methods:
        complete = [
            (index, batch)
            for index, batch in enumerate(evidence.batches)
            if batch.platform == platform
            and batch.method == method
            and len(batch.values) == 5
        ]
        if complete:
            index, _ = max(complete, key=lambda pair: (pair[1].window_end or pair[1].observed_at.date(), -pair[0]))
            return PlatformBasis(platform=platform, method=method, batch_index=index)
    return None


def _rank_scores(batch: SearchBatch) -> dict[str, float]:
    values = {item.candidate_id: item.value for item in batch.values}
    order = sorted(values.values(), reverse=batch.method != "related_rank")
    return {
        key: round(
            100
            * (
                len(order)
                - (
                    sum(
                        index + 1 for index, other in enumerate(order) if other == value
                    )
                    / order.count(value)
                )
            )
            / (len(order) - 1),
            4,
        )
        for key, value in values.items()
    }


def _passes_story(candidate: KeywordCandidate | InformationalKeywordCandidate) -> bool:
    if isinstance(candidate, InformationalKeywordCandidate):
        return candidate.eligibility
    scores = candidate.scores
    return (
        candidate.eligibility
        and scores.total >= 75
        and scores.relatability >= 18
        and scores.humor >= 18
        and scores.opening_hook >= 12
    )


def _rising(candidate: KeywordCandidate, evidence: KeywordEvidence) -> bool:
    return any(
        item.candidate_id == candidate.id
        and item.previous_value is not None
        and item.value > item.previous_value
        for batch in evidence.batches
        if batch.method != "related_rank"
        for item in batch.values
    )


def _official_event(candidate: KeywordCandidate, evidence: KeywordEvidence) -> bool:
    if candidate.event_date is None:
        return False
    delta = (candidate.event_date - evidence.researched_on).days
    return (candidate.event_kind == "deadline" and 0 <= delta <= 30) or (
        candidate.event_kind == "announcement" and -30 <= delta <= 0
    )


def select_topic(evidence: KeywordEvidence, requested: KeywordType) -> KeywordDecision:
    editorial = evidence.selection_policy == "editorial_v1"
    monthly = evidence.selection_policy in ("naver_monthly", "editorial_v1")
    bases = tuple(
        basis
        for platform in (("naver",) if monthly else PLATFORMS)
        if (basis := _basis(evidence, platform)) is not None
    )
    ranked = {
        basis.platform: (
            {item.candidate_id: item.value for item in evidence.batches[basis.batch_index].values}
            if monthly else _rank_scores(evidence.batches[basis.batch_index])
        )
        for basis in bases
    }
    eligible = tuple(
        candidate for candidate in evidence.candidates if _passes_story(candidate)
    )
    reason = "evergreen: sustained-demand candidates"
    effective: KeywordType = "evergreen"
    pool = tuple(
        candidate for candidate in eligible if candidate.keyword_type == "evergreen"
    )
    if requested == "trending":
        trending = tuple(
            candidate for candidate in eligible if candidate.keyword_type == "trending"
        )
        rising = tuple(
            candidate for candidate in trending if _rising(candidate, evidence)
        )
        events = tuple(
            candidate for candidate in trending if _official_event(candidate, evidence)
        )
        if rising:
            pool, effective, reason = (
                rising,
                "trending",
                "rising: observed increase across equal-duration windows",
            )
        elif events:
            pool, effective, reason = (
                events,
                "trending",
                "official_event fallback: no measured rising candidate",
            )
        else:
            reason = "evergreen fallback: no measured rise or timely official event"
    has_evidence = len(bases) == (1 if monthly else 2)
    positive = {
        candidate.id
        for candidate in pool
        if any(
            item.candidate_id == candidate.id and item.value > 0
            for basis in bases
            for item in evidence.batches[basis.batch_index].values
        )
    }
    pool_ids = {candidate.id for candidate in pool} & positive
    rows = []
    for candidate in evidence.candidates:
        naver = ranked.get("naver", {}).get(candidate.id)
        google = ranked.get("google", {}).get(candidate.id)
        total = (
            naver if monthly else round(naver * 0.6 + google * 0.4, 4)
            if naver is not None and google is not None
            else None
        )
        rejection = (
            ("missing complete Naver monthly PC + mobile counts" if monthly else "insufficient comparable evidence on both platforms")
            if not has_evidence
            else "audience/source/safety/duplicate gate failed"
            if isinstance(candidate, InformationalKeywordCandidate)
            and not _passes_story(candidate)
            else "story/safety/duplicate gate failed"
            if not _passes_story(candidate)
            else "outside current type/fallback tier"
            if candidate.id not in {item.id for item in pool}
            else "no observed positive demand"
            if candidate.id not in positive
            else None
        )
        rows.append(
            KeywordScore(
                candidate_id=candidate.id,
                editorial_total=candidate.editorial.total if editorial else None,
                naver=naver,
                google=google,
                total=total,
                rejection_reason=rejection,
            )
        )
    ranked_rows = tuple(
        row.model_copy(
            update={
                "rank": 1
                + sum(
                    other.total is not None and other.total > row.total
                    for other in rows
                )
            }
        )
        if row.total is not None
        else row
        for row in rows
    )
    if not has_evidence or not pool_ids:
        return KeywordDecision(
            status="hold",
            requested_type=requested,
            effective_type=None,
            selected_id=None,
            reason="insufficient comparable evidence"
            if not has_evidence
            else "no eligible demand candidate",
            evidence_label="insufficient",
            bases=bases,
            scores=ranked_rows,
        )
    totals = {row.candidate_id: row.total for row in rows if row.total is not None}
    winner = min(
        (item for item in pool if item.id in pool_ids),
        key=lambda item: (
            -(item.editorial.total) if editorial else 0,
            -totals[item.id],
            -item.scores.total if isinstance(item, KeywordCandidate) else 0,
            -item.scores.opening_hook if isinstance(item, KeywordCandidate) else 0,
            item.id,
        ),
    )
    if editorial:
        final_order = sorted((c for c in pool if c.id in pool_ids),
                             key=lambda c: (-c.editorial.total, -totals[c.id], c.id))
        final_ranks = {c.id: i + 1 for i, c in enumerate(final_order)}
        ranked_rows = tuple(row.model_copy(update={"final_rank": final_ranks.get(row.candidate_id)}) for row in ranked_rows)
        demand_leaders = [row for row in ranked_rows if row.rank == 1]
        leader_notes = []
        for row in demand_leaders:
            if row.candidate_id == winner.id:
                leader_notes.append(f"{row.candidate_id}: selected")
            else:
                leader_notes.append(f"{row.candidate_id}: {row.rejection_reason or 'lower editorial total or stable tie-break'}")
        reason += "; editorial_v1: AI editorial judgment, not measured Instagram performance; demand rank 1: " + "; ".join(leader_notes)
    scored = tuple(
        row.model_copy(update={"rejection_reason": "lower editorial total, monthly volume or stable tie-break" if editorial else "lower monthly volume or tie-break" if monthly else "lower weighted score or tie-break"})
        if row.candidate_id != winner.id and row.rejection_reason is None
        else row
        for row in ranked_rows
    )
    return KeywordDecision(
        status="selected",
        requested_type=requested,
        effective_type=effective,
        selected_id=winner.id,
        reason=reason,
        evidence_label="exact_monthly"
        if all(basis.method == "monthly_volume" for basis in bases)
        else "relative_proxy",
        bases=bases,
        scores=scored,
    )
