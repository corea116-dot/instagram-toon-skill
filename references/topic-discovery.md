# Topic Discovery

Use this contract only for a new `$instagram-toon` request with no user-supplied topic. It runs once as part of that request; it is not a background monitor or scheduled research process.

## Inputs and defaults

Read the current conversation, `memory/brand-bible.md`, `memory/banned-topics.json`, `memory/episode-history.json`, `memory/character-bible.json`, and `references/story-rules.md` before searching.

When the user did not supply other brief fields, use the established defaults: audience `일상 공감 독자`, tone `가벼운 공감 유머`, and character `bgoon`. Reuse any more specific values already present in the conversation or project. Never use employment status or workplace experience as a default audience, discovery filter, or score condition.

## ULW-research delegation and public-web boundary

For every automatic-topic invocation, EditorialScoutAgent must launch a bounded evidence-gathering subtask with an explicit `$ulw-research` prompt before it creates candidates. This is the only route that uses `$ulw-research`; a user-supplied topic and the explicit direct-Instagram-link route must not launch it.

Give the research task the current brand, banned-topic, episode-history, audience, tone, and character constraints. Require it to return an anonymized synthesis of general human observations and source metadata, not finished topics, dialogue, copied content, or episode files. Set its source priority as follows:

1. Normally accessible public Instagram posts, reels, and trend signals.
2. Normally accessible public community discussions.
3. Other public pages or official trend data only when they corroborate the first two territories or the prioritized territories have no usable safe signal.

Treat the ULW-research journal, report, and other working artifacts as temporary research state. Preserve only the short source metadata and anonymized observations required by `topic-research.json`, then remove the temporary workspace.

- Search only public pages and public trend data that the current Codex surface can access normally.
- Record likes, comments, reactions, or upvotes only when the count is visibly shown on that normally accessible page. Do not log in, estimate missing counts, infer hidden counts, or compare private analytics.
- For each candidate, derive `engagement_priority` from 0 to 100 only from its cited visible public-response evidence. Use `0` when no cited source displays a usable response count; never invent a value to favor a topic.
- Use public material as a signal for a general daily observation, never as copyable source material.
- Never log in, access private content, bypass restrictions, collect DMs, or reproduce a single person's post, wording, image, identity, or anecdote.
- Prefer two independent public pages for the selected candidate. One official trend source is sufficient when it is the direct source of the signal.
- Search the latest 30 days by default. Use older material only when it is clearly an evergreen daily observation rather than a claimed current trend.
- If the completed ULW-research task cannot access public evidence or produces no safe candidate, make five candidates from the brand, character, and episode-history memory. Mark the result `local_fallback` and state the exact fallback reason; never skip the ULW-research task merely to use this fallback.

## EditorialScoutAgent contract

Use a native `researcher` role when available to coordinate the explicit `$ulw-research` task. Do not substitute generic local public-web research. Give the agent only the inputs above and this contract. It returns either one structured selection result or a user-input request; it does not write episode files, publish anything, or draft final dialogue.

For a normal result, return exactly five candidates and one selected candidate. Every candidate contains:

- a concise Korean `topic`;
- `source_signal`, anonymized `human_observation`, and one-sentence `behavioral_contradiction`;
- `humor_engine_id` and a plain-language `engine_explanation`;
- `hook_seed`, `payoff_seed`, and an eligibility-bearing `gate_results` object;
- a one-sentence `story_seed` describing the comic mechanism, not a finished script;
- source IDs, unless `source_mode` is `local_fallback`;
- `engagement_priority` from 0 to 100, backed by at least one cited source's visible public-response count when it is greater than zero;
- five scores and their total, calculated only after the hard editorial gate.

The five candidates must use at least three distinct primary `humor_engine_id` values. The palette and definitions are in `references/story-rules.md`.

Score candidates out of 100:

| Dimension | Points | Pass intent |
| --- | ---: | --- |
| Relatability | 30 | A reader can immediately recognize the everyday friction. |
| Humor | 30 | Escalation and a fair short payoff are available. |
| Opening hook | 20 | A visually legible first image or concise line can stop the scroll. |
| Novelty | 10 | The comic mechanism differs from episode history. |
| Production fit | 10 | Sparse backgrounds, few props, clear action, and the established visual style can carry it. |

Select the **eligible** candidate with the highest `engagement_priority` first, then the highest total score. A candidate still needs a total of at least 75, relatability of at least 18, humor of at least 18, and opening hook of at least 12. When both priority and total tie, prefer the stronger opening hook, then the simpler drawable action. Keep the scoring and selection reason factual; never invent source evidence or response counts. `local_fallback` candidates must use priority `0`.

## Hard editorial gate before scoring

Evaluate every candidate before scoring. A candidate is ineligible if any gate fails; retain it in the five-candidate record with failure reasons.

1. **Source relevance:** its sources support the concrete human observation, not merely the broad topic domain.
2. **Contradiction clarity:** its behavioral mismatch fits one plain sentence.
3. **Comic mechanism:** its engine and how it creates the joke are explicit.
4. **Visual hookability:** a text-free or one-line first image is plausible.
5. **Payoff pressure:** a short reversal exists; “something happens” is not enough.
6. **Safety and originality:** banned material is absent and no history entry materially matches the beat signature or payoff.

Also reject a candidate before scoring when it:

- violates `hard_banned` rules;
- needs the `review_required` treatment and cannot be reframed safely;
- materially duplicates a stored beat signature or payoff (an engine match alone only lowers novelty);
- lacks the required public source support in `public_web` mode;
- depends on a real person's identity, a brand claim, a copied post, or a copyrighted character.

If no candidate passes, return this coordinator-only JSON and stop before writing an episode:

```json
{
  "outcome": "requires_user_input",
  "reason": "why all candidates failed",
  "safe_alternatives": ["optional short alternatives"]
}
```

The coordinator asks one short question only in that case. Otherwise it does not wait for topic approval: it records the selection and continues to IdeaAgent, WriterAgent, art, and QA.

## Episode record

For an automatic selection, set `brief.json.topic_origin` to `editorial_scout` and write `topic-research.json` before writing the final brief. Its schema is defined in `references/output-schema.md` and validated by `scripts/validate_episode.py`.

For a user-supplied topic, set `topic_origin` to `user`, do not call EditorialScoutAgent, and do not require `topic-research.json`. The user topic wins even if a current trend looks more attractive.

Under `## Agent QA` in `qa-report.md`, record the source mode, selected candidate ID, score total, selection reason, duplicate check, sensitivity check, and whether a local fallback was used. Store only short observations and source metadata, never copied source text or images.

## Story-quality gate (schema 1.1)

Before scoring, every candidate must pass: source relevance, a concrete human observation, behavioral contradiction, humor engine, hook seed, payoff seed, safety pass, and duplicate pass. Generate 5 candidates using 3+ humor engines in total; choose the highest-scoring eligible candidate. Matching beat signatures or payoffs are hard duplicates.
