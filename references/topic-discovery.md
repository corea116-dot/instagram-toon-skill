# Keyword Topic Discovery

Use for requested topic search or new episodes without a fixed topic. Information uses evidence 1.1 → research 1.3; humor uses evidence 1.0 → research 1.2. Historical records remain valid under their original rules. Direct topics are never replaced.

## Audience, goal, and rotation

Read the conversation, `memory/brand-bible.md`, `memory/banned-topics.json`, `memory/episode-history.json`, `memory/character-bible.json`, and `references/story-rules.md` first. Use explicit user constraints when present; the automatic-search defaults are:

- Audience: **20–30대 사회초년생**.
- Topic territories: **정부 지원 정책, 재테크, 경제, 주식투자, 부동산 투자뉴스**. Search across these territories unless the user limits the scope; do not force one candidate per territory when evidence favors another mix.
- Primary outcome: **조회·신규유입**. These are shared goals, not alternating keyword types or a guarantee of future performance.
- Tone: understandable, practical information with light relatable humor; character: `bgoon`.
- Requested keyword type: **단기 화제성 (`trending`) ↔ 지속 수요 (`evergreen`)**, starting with `trending` when no completed automatic search episode is recorded.

Read the next type through `topic_search.py plan`, not by calendar day or inference from the last topic. Only successful automatic keyword-search episode completions advance the rotation. Search-only runs, holds, failed collection/generation, manual-topic episodes, Instagram-link episodes, and repeated history updates do not consume another turn. Fallback changes the effective type for that run, not the requested rotation slot.

## Collect with Aside, decide locally

Read `aside-browser` and run its current `aside guide` before using the browser. Use `aside exec` for a bounded evidence-collection task. There is no mandatory `$ulw-research` stage. Aside collects observed data; the local selector normalizes scores and chooses the result. Do not ask the browser agent to invent values, choose the winner, or draft the comic.

From the skill root:

```bash
uv run scripts/topic_search.py plan --history memory/episode-history.json
uv run scripts/topic_search.py schema --output /absolute/project/keyword-evidence.schema.json
```

Read `references/keyword-evidence.md` for the exact input contract. Give Aside the requested type, audience/topic filters, banned/duplicate constraints, the evidence schema, and a short task along these lines:

> Read-only research for five Korean keyword candidates serving 20–30대 사회초년생. Collect comparable Naver and Google search-demand evidence, retaining the exact displayed value, unit, region, time window, access time, source URL, and limitations. Prefer actual monthly volumes already normally accessible; otherwise use comparable Naver DataLab/Google Trends relative indices or observed related-keyword ranks. Inspect official sources for policy/financial facts and dated timely triggers. Return observations and missing-data reasons, not a fabricated popularity estimate or winner. Do not register, log in, change account/settings, create ads, enable an API, pay, publish, or upload user files. Do not access private analytics or bypass restrictions.

Use `aside exec --permission guard` if supported by the current guide, with the scoped prompt above. `guard` is not itself a read-only guarantee; the task boundary still forbids external writes. Browser state may already permit a normal public view, but do not create new accounts or authorize spend to obtain data. API setup is not a prerequisite. If Aside is unavailable, report it; installation or a materially different collector requires the user's direction.

Preserve only short observations, source metadata, and the evidence needed to reproduce the comparison. No copied posts, images, personal anecdotes, or private account data. The coordinator writes `keyword-evidence.json`; the collector does not modify skill memory or episode history.

## Evidence and scoring rules

Collect **exactly five real candidates** with the content-type-specific fields in `references/keyword-evidence.md`. Information candidates compare demand, reader question, audience fit, official support, safety and duplication; do not draft five detailed stories. Include rejected candidates/reasons. Never fabricate missing candidates; fewer than five means preserve partial research and hold.

For each platform, use the highest-quality complete and comparable basis available for the five-candidate cohort:

1. Actual displayed monthly search volume, when all compared values share the same counting definition, period, region, and unit. A range, `<10`, or forecast is not an exact count.
2. Comparable relative indices from Naver DataLab or Google Trends, using a shared comparison/window. Separately normalized charts are not automatically comparable.
3. Actually observed related-keyword ranks, with a comparable ranking context and limitations recorded. Autocomplete position is a weak signal, not monthly search volume.

Do not mix raw counts, indices, rank positions, social likes, or search-result page counts. Missing evidence is not zero demand. If neither a complete comparable basis nor the permitted fallback is available for **either** platform, hold instead of silently dropping it or redistributing the weights.

The selector converts each platform's comparable ranks into a 0–100 percentile, using average ranks for ties, then calculates **Naver score × 0.6 + Google score × 0.4**. It retains the selected basis and original measurements. These are relative scores **within the observed candidate set**, not proof that a topic has the largest search volume on the whole platform. Label a mixed or proxy comparison as relative evidence; claim exact monthly volume only for the actual observed count and its period.

Keyword score is primary after eligibility and requested-type/fallback filtering. Information ties use ascending candidate ID; humor ties use story score, hook and ID. Use the selector result, not an agent's preferred winner. High demand cannot rescue failed gates.

## Timely and evergreen selection

For a `trending` slot, use eligible candidates in this order:

1. A measured rise supported by comparable recent/prior observations.
2. If none qualifies, an official event: an official announcement in the last 30 days or a confirmed upcoming application/event date within 30 days. Record the exact official URL and dates; do not describe an event-driven choice as a proven search surge.
3. If neither qualifies, an eligible `evergreen` candidate with comparable demand evidence. Record why the timely choices could not be used.

For an `evergreen` slot, choose an eligible persistent-demand candidate. Do not infer persistence from a one-day spike or an upcoming deadline alone. Evidence windows and the basis for the classification must be retained.

For selected policy, financial, economy, or investing information, verify claims against relevant official sources: agencies/program notices, regulators, official disclosures, exchange data, or issuer documentation as appropriate. Check dates, eligibility, exclusions, and whether an announcement is final. A news headline or search suggestion alone is not enough to assert an application schedule, benefit, return, or eligibility. No guaranteed-return framing, personalized buy/sell instruction, or invented deadline.

## Information eligibility

Evidence 1.1 has `content_type: informational` and four gates: `audience_fit`, `source_relevance`, `safety`, `duplicate`. All must pass and official supporting sources must resolve. It has no humor engine, hook/payoff seed or story score. Elaborate the selected question into a brief 1.2 question-answer card only after selection. See `informational-workflow.md`.

## Preserve the existing story gates (humor evidence 1.0 only)

Each candidate retains `source_signal`, `source_relevance`, a concrete anonymized `human_observation`, one-sentence `behavioral_contradiction`, `humor_engine_id`, `engine_explanation`, `hook_seed`, `payoff_seed`, `beat_signature`, `story_seed`, source IDs, `eligibility`, and all eight `gate_results`. Use at least three distinct primary humor engines across the five candidates.

Before score-based selection, require source relevance, human observation, behavioral contradiction, explicit humor mechanism, visual hook, short payoff, safety, and duplicate checks. Failed gates make the candidate ineligible and stay visible in the record. Matching beat signatures or payoffs are hard duplicates; matching an engine alone is not.

Retain the existing story score: relatability 0–30, humor 0–30, opening hook 0–20, novelty 0–10, production fit 0–10. A selected candidate needs total ≥75, relatability ≥18, humor ≥18, and hook ≥12. This score is a quality gate/tiebreak, not the demand metric.

## Select, hand off, or hold

Run the local selector after the evidence has been assembled:

```bash
uv run scripts/topic_search.py select \
  --evidence /absolute/project/keyword-evidence.json \
  --output /absolute/project/topic-research.json \
  --history memory/episode-history.json
```

Keep the generated `evidence` and `decision` together. Do not hand-edit computed scores, selected ID, requested/effective type, or fallback reasons. A malformed input is a collection/contract error to correct from actual evidence; it is not permission to invent measurements.

- **Selected, search-only:** show the topic, five-candidate ranking, evidence strength, reason, and file paths; stop before story modules/IdeaAgent and do not update history.
- **Selected, full episode:** retain the record in the episode, set `topic_origin: editorial_scout` and use the exact topic. Information continues with brief 1.2 and `informational-workflow.md`; humor keeps brief 1.1 and the existing story route.
- **Hold or unavailable collection:** show the exact missing evidence or failed gates and preserve available research. Stop before script/art and leave history unchanged. Do not use memory-only candidates as a successful search result.

At full-generation completion, record search evidence strength, source windows, requested/effective type, fallback, selected keyword/topic, weighted score, story gates, and official-fact checks in `## Agent QA`. After all required QA succeeds, write `review-state.json` according to `references/keyword-evidence.md`, then update history once. Leave the local draft at **검수 대기 (`review_pending`)**. No upload, publication, scheduler creation, or automatic approval is authorized by this workflow.
