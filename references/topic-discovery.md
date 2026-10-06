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

Read `aside-browser` and run its current `aside guide` before using the browser. Use a supported Aside execution route for bounded collection. Check the current guide/connection once. If a nested browser-agent model is unavailable, do not repeat it; use the documented direct REPL on the same browser and authorized account. Batch independent reads, keep navigation-dependent actions sequential. There is no mandatory `$ulw-research` stage. Aside collects observations; the coordinator adds concise editorial judgments and the local selector ranks them with observed demand. For current information, read `references/topic-editorial.md`; humor retains monthly-first selection. Do not ask the browser agent to invent values, choose the winner, or draft the comic.

From the skill root:

```bash
uv run scripts/topic_search.py plan --history memory/episode-history.json
uv run scripts/topic_search.py schema --output /absolute/project/keyword-evidence.schema.json
```

Read `references/keyword-evidence.md` for the exact input contract. Give Aside the requested type, audience/topic filters, banned/duplicate constraints, the evidence schema, and a short task along these lines:

> Collect up to fifteen lightweight source-backed discoveries across government support, salary/consumption, investment and housing. Record origin, date and audience relevance. Return observations, not a winner. After the coordinator narrows the pool, research only the five shortlisted Korean keywords for 20–30대 사회초년생. In Naver Ads keyword tool, record exact input/returned terms, monthly PC and mobile counts separately, reporting definition/window, region, access time and URL. Preserve `<10` and ranges verbatim, never as zero. Google Trends may support momentum but never substitutes for counts. Check official facts and dated triggers. Return observations and missing-data reasons, not a winner. Use existing sessions or explicitly authorized login only. Do not register, accept new terms, change settings, create ads, enable APIs, pay, publish, upload files or bypass restrictions.

Use `aside exec --permission guard` if supported. Reuse explicit authorization for the user's Naver blog account within scope; query Aside memory if account choice is unclear and never expose credentials. Stop for user action at MFA, registration or new terms. Login permission does not authorize payment, ads or API setup. API setup is not a prerequisite. If Aside is unavailable, report it; installation or a materially different collector requires user direction.

Preserve only short observations, source metadata, and the evidence needed to reproduce the comparison. No copied posts, images, personal anecdotes, or private account data. The coordinator writes `keyword-evidence.json`; the collector does not modify skill memory or episode history.

## Evidence and scoring rules

Naver's provider wording `최근 한달간` plus `observed_at` is a valid period record; do not require exact start/end dates if the tool omits them. Collect the five terms with the same definition/settings on the same day. Follow `keyword-evidence.md` for fields; no extra chart lookups solely for dates and no measured-growth claim from an undated snapshot.

For information, first normalize the lightweight discovery pool and retain shortlist/rejection reasons using `topic_search.py pool` as described in `topic-editorial.md`. Prefer at least three shortlisted territories, or record a user-scope/evidence exception. Then collect **exactly five real detailed candidates** with the content-type-specific fields in `references/keyword-evidence.md`. Information candidates compare demand, reader question, audience fit, official support, safety and duplication; do not draft five detailed stories. Include rejected candidates/reasons. Never fabricate missing candidates; fewer than five means preserve partial research and hold.

New information requires `selection_policy: editorial_v1`; humor requires `selection_policy: naver_monthly`. Collect a complete comparable Naver `monthly_volume` batch for five candidates: `pc_searches`, `mobile_searches`, and their sum as `value`. Definitions, period, region and filters must match. Preserve exact input/returned terms and actual reporting period; never invent a calendar month or substitute a related term's count.

Information ranks within the eligible type tier by editorial total, then monthly PC + mobile searches, then ascending ID. Humor ranks monthly counts first. Neither uses 60/40 weighting. Google Trends is auxiliary momentum/type evidence, never volume points. Missing Google data does not block a valid Naver comparison. Missing/incomplete Naver counts do block it. Ranges, `<10`, forecasts and estimates are not exact counts: retain raw observations, omit the numeric value and hold. Never pad with zero or fall back to relative proxies. Historical records without the new policy retain their original computation.

Show both monthly demand rank and final editorial rank, plus eligibility/type rejections and why the demand leader was not selected. Counts establish rank only within this cohort, not global popularity or guaranteed Instagram reach. Verify the winner's official facts before script handoff; if facts fail, mark the gate failed and recompute.

After eligibility and requested-type/fallback filtering, information uses the explicit three 0–2 editorial judgments in `topic-editorial.md`, then monthly counts and ID. These are AI editorial judgments, never measured Instagram performance or success probabilities. Humor uses monthly counts, then story score, hook and ID. Use the selector result, not an agent's preferred winner. High demand cannot rescue failed gates.

## Timely and evergreen selection

For a `trending` slot, use eligible candidates in this order:

1. A measured rise supported by comparable recent/prior observations.
2. If none qualifies, an official event: an official announcement in the last 30 days or a confirmed upcoming application/event date within 30 days. Record the exact official URL and dates; do not describe an event-driven choice as a proven search surge.
3. If neither qualifies, an eligible `evergreen` candidate with comparable demand evidence. Record why the timely choices could not be used.

For an `evergreen` slot, choose an eligible persistent-demand candidate. Do not infer persistence from a one-day spike or an upcoming deadline alone. Evidence windows and the basis for the classification must be retained.

For selected policy, financial, economy, or investing information, verify claims against relevant official sources: agencies/program notices, regulators, official disclosures, exchange data, or issuer documentation as appropriate. Check dates, eligibility, exclusions, and whether an announcement is final. A news headline or search suggestion alone is not enough to assert an application schedule, benefit, return, or eligibility. No guaranteed-return framing, personalized buy/sell instruction, or invented deadline.

## Information eligibility

Evidence 1.1 has `content_type: informational` and four gates: `audience_fit`, `source_relevance`, `safety`, `duplicate`. All must pass and official supporting sources must resolve. Under editorial_v1 it also requires discovery provenance and compact editorial directions; it has no humor engine or hook/payoff seed. Preserve the selected four-line direction without drafting alternate scripts. Elaborate the selected question into a brief 1.3 question-answer-action contract only after selection. See `informational-workflow.md`.

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
- **Selected, full episode:** retain the record in the episode, set `topic_origin: editorial_scout` and use the exact topic. New information continues with brief 1.3/script 1.2 and `informational-workflow.md`; humor keeps brief/script 1.1 and the existing story route.
- **Hold or unavailable collection:** show the exact missing evidence or failed gates and preserve available research. Stop before script/art and leave history unchanged. Do not use memory-only candidates as a successful search result.

At full-generation completion, record monthly PC/mobile counts, source windows, requested/effective type, fallback, selected keyword/topic, gates and official-fact checks in `## Agent QA`. After required QA succeeds, write `review-state.json` per `references/keyword-evidence.md`, then update history once. Leave the local draft at **검수 대기 (`review_pending`)**. No upload, publication, scheduler creation or automatic approval is authorized.
