# Instagram Toon Workflow

Use this workflow inside Codex Desktop, Codex CLI, or an IDE extension. Do not build or require a separate web application. The current Codex agent is the coordinator; delegate bounded specialist work to native Codex subagents and show progress, revision reasons, and QA results in the chat.

## Contents

- [Resolve the brief](#1-resolve-the-brief)
- [Route story modules](#2-route-story-modules)
- [Delegate bounded roles](#3-delegate-bounded-roles)
- [Keep the image provider replaceable](#4-keep-the-image-provider-replaceable)
- [Compose deterministically](#5-compose-deterministically)
- [Validate and record](#6-validate-and-record)

## 1. Resolve the brief

Accept either an explicit invocation such as `$instagram-toon 주제: ...` or a natural-language request to create a six-beat Instagram toon package. Resolve these fields from the current request, prior conversation, and project files before asking anything:

- `topic`
- `audience`
- `tone`
- `characters`

Run `InstagramPostAnalystAgent` first if the current request was explicitly invoked as `$instagram-toon` and contains exactly one direct Instagram post or reel link. Resolve the URL through `scripts/instagram_link_routing.py`, read `references/instagram-link-analysis.md`, set `brief.json.topic_origin` to `instagram_link`, and write `instagram-source.json` before IdeaAgent. This takes precedence over separately supplied topic wording, which becomes only an audience, tone, or analysis-angle constraint. A URL without an explicit invocation, an implicit skill selection, no URL, multiple URLs, profile URL, story, live, or non-Instagram URL must not activate this agent. An invalid or ambiguous URL asks for one direct post or reel URL. Public access failure asks for a permitted attachment or summary and stops; it never falls back to EditorialScoutAgent.

When the Instagram-link route did not activate and the user supplies a topic, set `brief.json.topic_origin` to `user`, use the supplied topic, and bypass EditorialScoutAgent completely. Never replace a user topic with a trend.

When the user invokes `$instagram-toon` without a topic, set `brief.json.topic_origin` to `editorial_scout`, read `references/topic-discovery.md`, and run EditorialScoutAgent before IdeaAgent. It must invoke `$ulw-research` for evidence gathering during that invocation, prioritizing normally accessible public Instagram signals and public community discussions. It must hard-gate exactly five candidates before scoring, use at least three primary humor engines, select the eligible candidate with the highest cited visible-engagement priority and then the highest story score, write 1.1 `topic-research.json`, and continue without waiting. Infer omitted audience, tone, and characters from memory; use the discovery reference defaults when needed. Ask the user only when no safe candidate passes or a sensitive ambiguity remains.

Never repeat a question whose answer is already available. Read the memory files before drafting. Use `memory/episode-history.json` to choose the next `EP-NNN` identifier and detect duplicate premises.

Create the episode under `episodes/EP-NNN-kebab-slug/`. Treat all episode files as drafts. Never publish, upload, schedule, or message an external service before the user explicitly approves that external action.

## 2. Route story modules

Run this stage only for a new episode or a story rewrite. Read `references/story-modules/router.md`, extract explicit `enable` and `disable` overrides from the request, evaluate mode, speaker count, serial/callback signals, story changes, and typed StoryCritic failures, then write `module-routing.json`. Set `brief.json.story_module_policy` to `auto_with_overrides` for new episodes created under this policy.

Read only files whose routing entry is `active`. The default new episode reads `story-architecture` and `storyboard-shot-plan`; `continuity-canon` and `dialogue-persona` require their own signal; `branch-payoff-lab` runs only for its typed failures and at most once. Disable wins over enable for the same ID. Recomposition, validation, and story-unchanged panel regeneration read no story modules. StoryCritic, safety, language, continuity QA, visual QA, and deterministic validation remain mandatory because they are gates, not optional modules.

Module outputs are narrow inputs to the existing contracts: architecture feeds IdeaAgent/WriterAgent; canon feeds ContinuityAgent; persona feeds DialogueNaturalnessAgent; one selected branch returns upstream before StoryCritic; shot planning feeds ArtDirectorAgent. Never persist their prose in `module-routing.json`, install the cited projects, or pass every module to a subagent.

## 3. Delegate bounded roles

Treat the specialist names below as task contracts, not custom `agent_type` values. Spawn an available native Codex role and include the specialist contract in its prompt. Prefer this mapping when the surface offers the role:

| Specialist contract | Native role |
| --- | --- |
| InstagramPostAnalystAgent | `researcher` or `vision` |
| EditorialScoutAgent | `researcher` coordinating an explicit `$ulw-research` task |
| IdeaAgent | `analyst` or `writer` |
| WriterAgent | `writer` |
| ContinuityAgent | `verifier` |
| DialogueNaturalnessAgent | `writer` or `critic` |
| ArtDirectorAgent | `designer` or `vision` |
| StoryCriticAgent | `critic` |
| VisualCriticAgent | `vision` or `verifier` |

The coordinator owns integration and all final decisions. Only the coordinator writes `brief.json`, `script.json`, history, and the consolidated QA report. A panel-generation worker may write only the one assigned `raw/panel-N.png`. No subagent may publish, update history, or modify another panel.

### InstagramPostAnalystAgent

Run only after the explicit one-link gate passes. Read one public linked post without login, crawling, comments, source download, or copied content. Read `references/instagram-link-analysis.md`, `memory/banned-topics.json`, and `memory/episode-history.json`. Return the 1.0 `instagram-source.json` contract: canonical URL, post type, public access result, abstract observation and contradiction, abstract hook/payoff patterns, candidate engines, excluded elements, changed story dimensions, ending-reversal reuse flag, duplicate result, and safety result. It never writes finished dialogue or images. A private, login-gated, removed, restricted, or insufficiently visible post returns `requires_user_input` and ends this episode attempt before IdeaAgent.

### EditorialScoutAgent

Run only for a new invocation with no user topic. Read `references/topic-discovery.md`, `memory/brand-bible.md`, `memory/banned-topics.json`, `memory/episode-history.json`, and the current brief defaults. Delegate the research subtask with an explicit `$ulw-research` prompt; do not replace it with generic local browsing. Scope that task to public material only, with source priority of (1) normally accessible public Instagram posts, reels, and trend signals, then (2) normally accessible public community discussions, and finally (3) other public or official trend sources only when corroboration or availability requires them. Do not log in, scrape restricted material, bypass access controls, or copy a person's post, wording, image, identity, or anecdote. The research task returns only an anonymized source synthesis; EditorialScoutAgent turns that synthesis into the five candidates and removes any temporary research workspace after retaining the required `topic-research.json` metadata.

Return exactly five candidates and one selected candidate matching 1.1 `topic-research.json`. Before scoring, each candidate must pass source relevance for its concrete observation, contradiction clarity, explicit comic mechanism, visual hookability, payoff pressure, and safety/originality. Keep failed candidates with reasons but make them ineligible. Record only publicly visible likes, comments, reactions, or upvotes from normally accessible pages, normalize each candidate's cited evidence to `engagement_priority` 0–100, and never estimate unavailable metrics. The selected candidate must have the highest eligible engagement priority and then the highest story score, total at least 75, relatability at least 18/30, humor at least 18/30, and opening hook at least 12/20. Require two public pages for the selected candidate, except one official trend source. Record short source metadata and an anonymized observation only. If web research fails, use the documented local fallback and record why. If no candidate is safe and distinct, return the `requires_user_input` result from `topic-discovery.md`; the coordinator asks once and stops before IdeaAgent.

### IdeaAgent

Read the brief, `memory/banned-topics.json`, and `memory/episode-history.json`. Return JSON with exactly three distinct 1.1 directions, duplicate findings, and sensitivity findings. Each direction needs `premise`, `human_truth`, `behavioral_contradiction`, `humor_engine_id`, `engine_explanation`, `hook_promise`, exactly four distinct visible `development_changes`, `payoff_reversal`, `beat_signature`, and `why_relatable`; across all three use at least two primary engines. Do not write finished dialogue.

### WriterAgent

Read the chosen direction plus `references/story-rules.md` and `references/output-schema.md`. Return one `script.json` object with exactly six panels: one opening hook, four development beats, and one ending payoff. Panel 1 must use a strong visual hook, concise dialogue hook, or both; it must create a concrete reason to continue without revealing the ending. Include section, beat, scene, expression, action, props, background, camera, and no more than two dialogue bubbles per panel.

### StoryCriticAgent

Use two stages. **Premise mode** runs after IdeaAgent and before WriterAgent: review all directions against contradiction, engine, hook, four-change, payoff, duplicate, and safety gates; return passing IDs plus typed failure classifications and a reroute. **Script mode** runs after WriterAgent: score the five dimensions in `references/qa-rubric.md` and enforce all hard gates independently. A script passes only with at least 80 and no hard failure. Return `failure_class`, `reroute_to`, `hook_question`, and payoff-reframing evidence. Send concrete `revision_instructions` to WriterAgent only for script-local failures. Permit at most two script rewrite rounds; route topic and mechanism failures upstream, never to art. If the best permitted path fails, mark story QA failed, report unresolved issues, and stop before image generation unless the user explicitly accepts the draft.

### DialogueNaturalnessAgent

Run only after StoryCriticAgent passes and before ArtDirectorAgent starts. Read the current brief, script, `references/dialogue-naturalness.md`, `references/story-rules.md`, `memory/dialogue-style.md`, and the speaking-character entries in `memory/character-bible.json`. Return only the JSON contract in `references/dialogue-naturalness.md`.

This is a conservative wording gate, not a second writing pass: check literal or stiff phrasing, needless formalization, dialogue that explains visible action, and character-voice mismatches. Preserve the beat sequence, facts, joke and twist, speaker, bubble count, geometry, named entities, numbers, time expressions, quotations, intentional fragments, repetitions, pauses, laughter, and register. The coordinator may apply one safe revision round only. If a proposed revision would materially change pacing or the comic mechanism, leave it as a finding and set `requires_story_recheck` rather than making the edit. A requested story recheck must pass before art begins.

### ContinuityAgent

Read `memory/character-bible.json`, `memory/visual-style.json`, and the current script. Check face, hair, outfit, palette, props, voice, background, time, positions, and state changes. Return panel-addressed JSON corrections. Apply corrections to the script or panel prompts before image generation.

### ArtDirectorAgent

Read character reference paths from `memory/character-bible.json` and the full policy in `memory/visual-style.json`. First settle a single six-beat storyboard and camera plan. Compose panel 1 for instant mobile-feed impact with a clear focal subject, strong expression or action, and uncluttered hook dialogue space when used. Then produce `prompts/panel-N.json` and generate panels in order 1 through 6, using prior panels as continuity context where the available image tool permits.

For every new panel and every user-requested targeted regeneration, put the three ordered `primary_reference_images` in `reference_images` before any character path. Enforce their strict palette, one flat or nearly empty background, two-prop maximum, and playful-but-quiet mood in both `prompt` and `negative_prompt`. Use the images only for those style properties; never copy their cat, characters, scene, props, pose, text, watermark, signature, or logo. If character visuals conflict with the primary style, prioritize the primary style. Never request text, captions, lettering, speech bubbles, UI text, watermarks, or signatures inside generated art.

### VisualCriticAgent

Inspect the raw panels against the final script, `references/visual-rules.md`, and the active primary-reference policy. Return the JSON contract from `references/qa-rubric.md`, including panel number, problem, severity, and a ready-to-use revision prompt. Explicitly check strict palette adherence, very sparse background/prop density, and the playful-but-quiet mood. Regenerate only the failing panel once for a primary-reference style failure, then rerun continuity and visual checks for that panel and its immediate neighbors. If the retry still fails, record review required instead of retrying again.

## 4. Keep the image provider replaceable

The stable provider boundary is:

```text
prompts/panel-N.json -> image provider -> raw/panel-N.png (1080x1350)
```

For version 1, prefer the image generation feature available to the current Codex surface. In mock mode, `compose_episode.py` deterministically creates the same `raw/panel-N.png` contract without a network call. A future `scripts/generate_panel.py` may implement the OpenAI Image API, but it must consume `schema_version`, `panel`, `revision`, `mode`, `size`, `prompt`, `negative_prompt`, `reference_images`, `bubble_safe_areas`, and `continuity` from the same prompt JSON and produce the same PNG path; composition, validation, and history scripts must not import or call a provider SDK. Every provider must output an exact 1080x1350 PNG.

Store user-supplied character images under `assets/references/characters/` and style images under `assets/references/styles/`, then record their project-relative paths in the corresponding memory JSON. Do not embed image binaries in JSON.

## 5. Compose deterministically

Insert Korean dialogue only after raw art exists. The composer owns font selection, wrapping, font-size reduction, bubble geometry, placement, the opening/development/ending delivery layout, PNG encoding, and file names. Generated art remains text-free.

Run a full mock composition:

```bash
uv run scripts/compose_episode.py --episode-dir episodes/EP-001-example --mock
```

Regenerate and recompose only panel 3:

```bash
uv run scripts/compose_episode.py --episode-dir episodes/EP-001-example --mock --panel 3
```

Single-panel mode reads the existing prompt manifest and increments its `revision` automatically. It may change only the named prompt, raw panel, and internal `composed/panel-N.png`; then it changes exactly one final image: `final/opening.png` for panel 1, `final/development-four-panel.png` for panels 2–5, or `final/ending.png` for panel 6. Other prompt manifests, raw panels, composed panels, and final images must remain byte-for-byte unchanged.

## 6. Validate and record

Validate before presenting results. Include the InstagramPostAnalystAgent or EditorialScoutAgent result when used, plus StoryCriticAgent, DialogueNaturalnessAgent, ContinuityAgent, and VisualCriticAgent results in `## Agent QA`:

```bash
uv run scripts/validate_episode.py --episode-dir episodes/EP-001-example
uv run scripts/update_history.py \
  --episode-dir episodes/EP-001-example \
  --history memory/episode-history.json \
  --status draft
```

Success must print the resulting path. Failure must print an understandable error to stderr and return a nonzero exit code. Require all paths listed in `references/output-schema.md`, valid JSON, a valid `module-routing.json` whenever `story_module_policy` is `auto_with_overrides`, a valid `topic-research.json` whenever `topic_origin` is `editorial_scout`, a valid `instagram-source.json` whenever `topic_origin` is `instagram_link`, six panels in the required section and beat order, at most two bubbles per panel, three 1080x1350 final PNGs, and 1080x1350 internal composed panels. Historical briefs without the policy marker remain readable, and the deterministic tools may still read exact four-panel legacy episodes for targeted recomposition. Write deterministic findings and a compact active/skipped module summary to `qa-report.md` without discarding an existing Agent QA section, then summarize both agent and script results in chat.

Remove temporary files and staging directories created during the run. Preserve episode artifacts, user reference images, and memory. Stop before any external publishing step unless the user has explicitly approved it.

## Story-quality gate (schema 1.1)

Idea returns exactly 3 rich directions using 2+ humor engines. StoryCritic runs a premise stage, then a script stage, classifying failures as: topic, mechanism, hook, beats, payoff, dialogue, duplicate, safety, or visual; allow at most 2 rewrites. User-supplied topics bypass the scout. Never use profanity or obfuscated profanity; blunt, non-profane Korean is allowed.
