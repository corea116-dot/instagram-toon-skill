# Source-backed discovery and editorial_v1

Applies to new automatic informational topic selection, including search-only. Explicit user topics remain unchanged; historical saved policies replay as recorded. This is an initial operating rule to test, not a proven Instagram performance formula. Read alongside `keyword-evidence.md` for measured-demand and official-fact requirements.

## Light pool → five detailed candidates → one script

1. Reuse dated prior candidates and inspect official announcements/dates and actually observed related keywords. Supplied comments/insights can contribute when available. Do not invent popularity or source observations from model recall.
2. Record **at most 15** lightweight discoveries, not a quota: `id`, `keyword`, `domain`, `source_kind`, `source_reference`, `observed_on`, `audience_relevance`, `shortlist`, `decision_reason`. References are real page URLs or specific local evidence paths/record IDs. Old observations remain dated; do not relabel them as fresh.
3. Record `coverage` for all four domains: `government_support`, `salary_consumption`, `investment`, `housing`. Explain areas with no useful evidence. Prefer five shortlisted candidates spanning at least three domains. If scope is user-constrained or evidence insufficient, provide `diversity_exception`; never create filler candidates. Domain reflects the reader problem, not merely a broad category label.
4. The coordinator supplies reasoned shortlist decisions. Local code normalizes Unicode/whitespace/case duplicates, preserves every original observation and reason, and checks five unique shortlisted candidates. It does not pretend to choose the best candidates semantically. For synonymous keywords or repeated story angles, perform the existing semantic duplicate check too.
5. Collect comparable Naver monthly PC/mobile counts and relevant official eligibility evidence for **only those five**. Reuse same-day/same-settings measurements where valid. Verify current dates, terms and official facts before production.

```bash
uv run scripts/topic_search.py pool-schema > /absolute/attempt/discovery.schema.json
uv run scripts/topic_search.py pool --input /absolute/attempt/discovery.json --output /absolute/attempt/discovery-report.json
uv run scripts/topic_search.py schema --output /absolute/attempt/keyword-evidence.schema.json
```

Pool input: `schema_version: "1.0"`, `researched_on`, `candidates`, `coverage`, optional `diversity_exception`. `pool` returns 0 ready, 2 hold, 1 malformed/I/O. Preserve partial evidence on hold and stop before drafting. Embed the original validated pool as `discovery` in evidence; its shortlist IDs/keywords must match the five detailed candidates. `researched_on` is the current review date; individual `observed_on` dates preserve age.

## Four-line directions and explicit judgment

The existing creator, in one bounded pass, supplies each candidate's `editorial`:

- `reader_situation`: whose concrete situation?
- `opening_question`: why turn the page? Must exactly match `reader_question`.
- `answer_action`: the supported answer and next action.
- `save_share_use`: a specific later use or recipient; do not claim predicted shares.

Three ratings, each `{value: 0|1|2, reason: "concrete explanation"}`:

| Rating | 0 insufficient | 1 adequate | 2 clear |
| --- | --- | --- | --- |
| `reader_relevance` | Reader situation unclear | Relevant broad concern | Specific social-beginner situation and consequence |
| `episode_clarity` | Question/answer unclear or too broad | Feasible question and answer | One clear question with a bounded, official-source-supported answer |
| `practical_value` | No useful next action/use | General practical use | Concrete action, checklist or identifiable sharing situation |

Set `judgment_kind: ai_editorial_judgment`. These are **AI editorial judgments**, not observed demand, measured Instagram response, or probability of success. No five full scripts, long alternative titles or extra review roles.

Hard eligibility gates, official sources, complete exact Naver counts, positive demand and requested-type/fallback tier apply first. Then sort by **editorial total descending → Naver monthly PC+mobile descending → candidate ID ascending**. Existing trend/event/evergreen fallbacks remain. Zero/weak judgments cannot rescue failed gates; missing comparable demand means hold.

`decision.scores[].rank` is demand rank; `editorial_total` is 0–6; `final_rank` is the rank among eligible current-tier positive-demand candidates, null otherwise. Display both rankings, the explained judgments and demand leader rejection. `exact_monthly` labels the demand measurement only. Research retains the full evidence for reproducibility; CLI stdout also supplies the selected `creator_handoff`. Give that selected direction to the same creator without restarting concept generation. Only one full script proceeds to unchanged content/visual QA.

## Supplied performance data (advisory only)

No API, login, scraping, publishing or scheduled collection is added. When the user supplies local insights, export the schema and summarize them:

```bash
uv run scripts/topic_search.py performance-schema > /absolute/project/insights.schema.json
uv run scripts/topic_search.py performance --input /absolute/project/insights.json --output /absolute/project/insights-summary.json
```

Input `schema_version: "1.0"`, `posts`. Per post record ID, source reference, timezone-aware publication/window-end/collection times, `paid` true/false/null, `domain`, `story_approach`, and actual nonnegative integer `views`, `reach`, `nonfollower_reach`, post-attributed `follows`, `shares`, `saves`. Missing metrics are null with a reason in `missing_reasons`; paid unknown also needs a reason. Do not infer post-attributed follows from whole-account follower growth or counts from unavailable percentages. One observation per post; replace that record when correcting supplied data.

Only exact **seven-day post-publication windows** enter comparisons. Other periods remain listed as excluded, without extrapolation. Groups separate domain, story approach and paid/organic/unknown status. Each metric reports observed total, observed/missing sample counts, and per-1,000-reach rates computed only from posts where both that metric and positive reach are present. Rate sample counts and denominators remain visible. Missing is never zero. Empty, small-sample and novel topics receive no penalty.

Read the summary during discovery as advisory context. Prioritize views, nonfollower reach and attributed follows; shares/saves are auxiliary. Keep sample counts visible; never infer causation or use automatic learned weights from this summary. If it suggests a hypothesis, record that as the reason to test a future topic/approach, not a proven advantage. The selector takes no performance multiplier. Repeated identical input reuses the existing summary without rewriting; refresh only for supplied new/corrected input. Automatic weighting requires separate validation and scope.
