# Instagram Toon Workflow

Current topic-search policy overrides the legacy 60/40 and proxy instructions below: follow `keyword-evidence.md` and `topic-editorial.md`: new information ranks explicit editorial judgments then Naver monthly PC + mobile counts; humor ranks monthly counts first. Google is auxiliary only. Detailed collection remains five candidates; new information begins with a source-backed lightweight pool of up to fifteen. For Naver's `최근 한달간`, preserve the provider wording plus observation timestamp; exact start/end dates are optional and must not be invented. Missing counts still cause hold, but absent exact dates alone do not.

Use this workflow inside Codex Desktop, Codex CLI, or an IDE extension. Do not build or require a separate web application. The current Codex agent is the coordinator; delegate bounded specialist work to native Codex subagents and show progress, revision reasons, and QA results in the chat.

## Route by content type

For policy/finance/economy/investing/news, follow `informational-workflow.md` instead of sections 2–3's humor roles. New episodes use brief 1.3, script 1.2, evidence 1.1/research 1.3; historical 1.2/1.1 information remains readable. Keep request/link/privacy and composition/file safeguards. Information has one integrated content review, a semantic content lock and a deterministic layout preflight, not separate premise/Story/Dialogue/Continuity passes. Modules are optional; policy marker is required only when opting into routing. Remaining three-direction/engine/score rules describe the preserved humor route. Resolve references once per generation batch (refresh on changes/new batch), inspect final pages in order, and inspect raw only for suspected defects.

## Contents

- [Resolve the brief](#1-resolve-the-brief)
- [Route story modules](#2-route-story-modules)
- [Delegate bounded roles](#3-delegate-bounded-roles)
- [Keep the image provider replaceable](#4-keep-the-image-provider-replaceable)
- [Compose deterministically](#5-compose-deterministically)
- [Validate and record](#6-validate-and-record)

## 1. Resolve the brief

Accept either an explicit invocation such as `$instagram-toon 주제: ...` or a natural-language request to create an Instagram toon package. Resolve these fields from the current request, prior conversation, and project files before asking anything:

- `topic`
- `audience`
- `tone`
- `characters`
- `output_layout`

Parse explicit output requests into page sizes: `2컷+3컷` becomes `[2, 3]` and `1컷짜리 5장` becomes `[1, 1, 1, 1, 1]`. Default to `[1, 1, 1, 1, 1]` when no output shape is requested. A page may contain one to four panels, and the sum is the story panel count. New scripts use schema 1.1 and record this array in `script.json`.

Run `InstagramPostAnalystAgent` first if the current request was explicitly invoked as `$instagram-toon` and contains exactly one direct Instagram post or reel link. Resolve the URL through `scripts/instagram_link_routing.py`, read `references/instagram-link-analysis.md`, set `brief.json.topic_origin` to `instagram_link`, and write `instagram-source.json` before IdeaAgent. This takes precedence over separately supplied topic wording, which becomes only an audience, tone, or analysis-angle constraint. A URL without an explicit invocation, an implicit skill selection, no URL, multiple URLs, profile URL, story, live, or non-Instagram URL must not activate this agent. An invalid or ambiguous URL asks for one direct post or reel URL. Public access failure asks for a permitted attachment or summary and stops; it never falls back to EditorialScoutAgent.

When the Instagram-link route did not activate and the user supplies a topic, set `brief.json.topic_origin` to `user`, use the supplied topic, and bypass EditorialScoutAgent completely. Never replace a user topic with a trend.

When asked to search/select a topic or create a new episode without a fixed topic, set `brief.json.topic_origin` to `editorial_scout`, read `references/topic-discovery.md` and `references/keyword-evidence.md`, and run EditorialScoutAgent before the content-type route. Its Aside collection and deterministic `topic_search.py` selection replace public-engagement scouting for new automatic records. The defaults are 20–30대 사회초년생, the agreed policy/finance/economy/investing territories, and 조회·신규유입. Rank comparable Naver/Google search evidence at 60%/40%. Information writes research 1.3 and continues to brief 1.3; humor writes research 1.2 and continues to brief 1.1 with its story gates. A missing-evidence hold ends before drafting without changing history. On a valid selection, continue without another topic interview unless the user requested search-only.

For `주제 검색만` or equivalent search-only requests, return the evidence, ranking, and selected topic or hold reason, then stop. Do not route story modules, draft scripts, generate images, or update history. A broad category constraint is a search filter; a fixed user topic still bypasses the scout.

Never repeat a question whose answer is already available. Read the memory files before drafting. Use `memory/episode-history.json` to choose the next `EP-NNN` identifier and detect duplicate premises.

Create the episode under `episodes/EP-NNN-kebab-slug/`. Treat all episode files as drafts. Never publish, upload, schedule, or message an external service before the user explicitly approves that external action.

## 2. Route story modules

Run this stage only for a new episode or a story rewrite. Read `references/story-modules/router.md`, extract explicit `enable` and `disable` overrides from the request, evaluate mode, speaker count, serial/callback signals, story changes, and typed StoryCritic failures, then write `module-routing.json`. Set `brief.json.story_module_policy` to `auto_with_overrides` for new episodes created under this policy.

Read only files whose routing entry is `active`. The default new episode reads `story-architecture` and `storyboard-shot-plan`; `continuity-canon` and `dialogue-persona` require their own signal; `branch-payoff-lab` runs only for its typed failures and at most once. Disable wins over enable for the same ID. Recomposition, validation, and story-unchanged panel regeneration read no story modules. StoryCritic, safety, language, continuity QA, visual QA, and deterministic validation remain mandatory because they are gates, not optional modules.

Module outputs are narrow inputs to the existing contracts: architecture feeds IdeaAgent/WriterAgent; canon feeds ContinuityAgent; persona feeds DialogueNaturalnessAgent; one selected branch returns upstream before StoryCritic; shot planning feeds ArtDirectorAgent. Never persist their prose in `module-routing.json`, install the cited projects, or pass every module to a subagent.

## 3. Delegate bounded roles

Treat the specialist names below as task contracts, not custom `agent_type` values. Use the configured `toon_*` roles and exact model/effort policy in `model-routing.md` first. The following generic mapping is only descriptive fallback guidance; it must not bypass that model policy. Include the specialist contract in the bounded handoff:

| Specialist contract | Native role |
| --- | --- |
| InstagramPostAnalystAgent | `researcher` or `vision` |
| EditorialScoutAgent | `researcher` collecting with Aside; coordinator runs the deterministic selector |
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

Run only within a requested topic-search or new-episode run with no fixed user topic. Read `references/topic-discovery.md`, `references/keyword-evidence.md`, the banned-topic/history/brand constraints, and `aside-browser` with its current guide. The coordinator first runs `topic_search.py plan --history memory/episode-history.json` to derive the next requested `trending` or `evergreen` slot. Only successfully completed automatic keyword-search episodes advance that slot; retries, failures, search-only runs, and manual topics do not.

Use Aside for bounded read-only collection of exactly five keyword candidates. Prefer actual monthly counts when the whole comparison cohort has matching units/windows/region; otherwise collect comparable DataLab/Google Trends indices or related-keyword ranks. Retain original values, method, dates, source URLs, and limitations. No account creation, login, advertising/API setup, payment, private metrics, posting, restriction bypass, or invented missing values. Broad topic domains are search filters, not proof of popularity. Do not require `$ulw-research` or rank by social likes.

Preserve every existing source/story field, all eight hard gates, five story-score dimensions, and three or more distinct humor engines. Keep failed candidates and reasons, but exclude them from selection. A selected candidate needs story total ≥75, relatability ≥18, humor ≥18, hook ≥12, and official sources for policy/financial facts. For a timely slot, try measured rising demand, then a dated official event in the documented 30-day window, then an evergreen fallback with a reason.

The coordinator writes `keyword-evidence.json` and runs `topic_search.py select --evidence ... --output ... --history ...`. The selector performs per-platform rank normalization, weights Naver 60% + Google 40%, applies the content-type tie rules, and returns an information 1.3 or humor 1.2 selection/hold while preserving evidence. Do not edit its computed decision to favor a candidate. Insufficient comparable evidence on either platform, failed editorial gates, or incomplete collection stops before drafting without a memory-only fallback or history update. Search-only success stops at the research artifact; full-generation success passes the selected topic to the appropriate downstream workflow. Follow `references/keyword-evidence.md` for the QA-bound `review-state.json` needed before recording a successful keyword-search completion.

### IdeaAgent

Read the brief, including its selected `output_layout`, plus `memory/banned-topics.json` and `memory/episode-history.json`. Return JSON with exactly three distinct 1.1 directions, duplicate findings, and sensitivity findings. Each direction needs one distinct visible `development_change` per inner panel in the selected layout, plus `premise`, `human_truth`, `behavioral_contradiction`, `humor_engine_id`, `engine_explanation`, `hook_promise`, `payoff_reversal`, `beat_signature`, and `why_relatable`; across all three use at least two primary engines. Do not write finished dialogue.

### WriterAgent

Read the chosen direction plus `references/story-rules.md` and `references/output-schema.md`. Return one schema 1.1 `script.json` object whose `output_layout` matches the request: one opening hook, one or more development beats, and one ending payoff. Panel 1 must use a strong visual hook, concise dialogue hook, or both; it must create a concrete reason to continue without revealing the ending. Include section, beat, scene, expression, action, props, background, camera, and no more than two dialogue bubbles per panel.

### StoryCriticAgent

Use two stages. **Premise mode** runs after IdeaAgent and before WriterAgent: review all directions against contradiction, engine, hook, four-change, payoff, duplicate, and safety gates; return passing IDs plus typed failure classifications and a reroute. **Script mode** runs after WriterAgent: score the five dimensions in `references/qa-rubric.md` and enforce all hard gates independently. A script passes only with at least 80 and no hard failure. Return `failure_class`, `reroute_to`, `hook_question`, and payoff-reframing evidence. Send concrete `revision_instructions` to WriterAgent only for script-local failures. Permit at most two script rewrite rounds; route topic and mechanism failures upstream, never to art. If the best permitted path fails, mark story QA failed, report unresolved issues, and stop before image generation unless the user explicitly accepts the draft.

### DialogueNaturalnessAgent

Run only after StoryCriticAgent passes and before ArtDirectorAgent starts. Read the current brief, script, `references/dialogue-naturalness.md`, `references/story-rules.md`, `memory/dialogue-style.md`, and the speaking-character entries in `memory/character-bible.json`. Return only the JSON contract in `references/dialogue-naturalness.md`.

This is a conservative wording gate, not a second writing pass: check literal or stiff phrasing, needless formalization, dialogue that explains visible action, and character-voice mismatches. Preserve the beat sequence, facts, joke and twist, speaker, bubble count, geometry, named entities, numbers, time expressions, quotations, intentional fragments, repetitions, pauses, laughter, and register. The coordinator may apply one safe revision round only. If a proposed revision would materially change pacing or the comic mechanism, leave it as a finding and set `requires_story_recheck` rather than making the edit. A requested story recheck must pass before art begins.

### ContinuityAgent

Read `memory/character-bible.json`, `memory/visual-style.json`, and the current script. Check face, hair, outfit, palette, props, voice, background, time, positions, and state changes. Return panel-addressed JSON corrections. Apply corrections to the script or panel prompts before image generation.

### ArtDirectorAgent

Read character reference paths from `memory/character-bible.json` and the full policy in `memory/visual-style.json`. First settle a storyboard and camera plan matching the selected `output_layout`. Compose panel 1 for instant mobile-feed impact with a clear focal subject, strong expression or action, and uncluttered hook dialogue space when used. Then produce `prompts/panel-N.json` and generate panels in order, using prior panels as continuity context where the available image tool permits.

For every new panel and every user-requested targeted regeneration, run `uv run scripts/active_reference.py` immediately before building provider prompts. Resolve the shared character/style directory marker to all reported image paths; put character references first in `reference_images`, then all primary style references, and deduplicate shared images. Never attach the directory itself or removed images from prior prompts. Enforce the immutable character traits from the character bible before applying the style palette, planned mood, and scene policy in `visual-rules.md`. Style references may not alter face, hair, beard, skin tone, body proportions, or expression grammar. Use `wardrobe_overrides` only when the script gives a `story_reason`, and carry the resulting outfit and footwear through later panels. Never request text, captions, lettering, speech bubbles, UI text, watermarks, or signatures inside generated art.

### VisualCriticAgent

Inspect the raw panels against the final script, `references/visual-rules.md`, and the active primary-reference policy. Return the JSON contract from `references/qa-rubric.md`, including panel number, problem, severity, and a ready-to-use revision prompt. Explicitly check palette adherence, planned cast/action/setting, readable scene density, and the planned mood. Regenerate only the failing panel once for a primary-reference style failure, then rerun continuity and visual checks for that panel and its immediate neighbors. If the retry still fails, record review required instead of retrying again.

## 4. Keep the image provider replaceable

The stable provider boundary is:

```text
prompts/panel-N.json -> image provider -> raw/panel-N.png (manifest size)
```

For version 1, prefer the image generation feature available to the current Codex surface. In mock mode, `compose_episode.py` deterministically creates the same `raw/panel-N.png` contract without a network call. A future `scripts/generate_panel.py` may implement the OpenAI Image API, but it must consume `schema_version`, `panel`, `revision`, `mode`, `size`, `prompt`, `negative_prompt`, `reference_images`, `bubble_safe_areas`, and `continuity` from the same prompt JSON and produce the same PNG path; composition, validation, and history scripts must not import or call a provider SDK. Normalize provider art proportionally to manifest size before lettering; `frame_native_v1` uses native slot dimensions, legacy uses 1080×1350.

Store shared character/style references directly under `assets/references/styles/`; every supported image directly in that folder is auto-attached without editing memory JSON. Store separate character-only images under `assets/references/characters/` and register those paths in the character bible. Do not embed image binaries in JSON.

## 5. Compose deterministically

Insert Korean dialogue only after raw art exists. The composer owns font selection, wrapping, font-size reduction, bubble geometry, placement, the selected page layout, PNG encoding, and file names. Generated art remains text-free. Use the common body-and-tail union renderer for every speech bubble; apply the seam-free composition and final-review rules in `visual-rules.md`.

Run a full mock composition:

```bash
uv run scripts/compose_episode.py --episode-dir episodes/EP-001-example --mock
```

Regenerate and recompose only panel 3:

```bash
uv run scripts/compose_episode.py --episode-dir episodes/EP-001-example --mock --panel 3
```

Single-panel mode reads the existing prompt manifest and increments its `revision` automatically. It may change only the named prompt, raw panel, and internal `composed/panel-N.png`; then it changes exactly one `final/page-NN.png` containing that panel. Other prompt manifests, raw panels, composed panels, and final images must remain byte-for-byte unchanged. Schema 1.0 episodes retain their legacy target mapping.

## 6. Validate and record

Validate before presenting results. Include the InstagramPostAnalystAgent or EditorialScoutAgent result when used, plus StoryCriticAgent, DialogueNaturalnessAgent, ContinuityAgent, and VisualCriticAgent results in `## Agent QA`:

```bash
uv run scripts/validate_episode.py --episode-dir episodes/EP-001-example
uv run scripts/update_history.py \
  --episode-dir episodes/EP-001-example \
  --history memory/episode-history.json \
  --status draft
```

Success must print the resulting path. Failure must print an understandable error to stderr and return a nonzero exit code. Require all paths listed in `references/output-schema.md`, valid JSON, a valid `module-routing.json` whenever `story_module_policy` is `auto_with_overrides`, a valid `topic-research.json` whenever `topic_origin` is `editorial_scout`, a valid `instagram-source.json` whenever `topic_origin` is `instagram_link`, an opening, one or more development panels, an ending, at most two bubbles per panel, one 1080x1350 final PNG per requested output group, and 1080x1350 internal composed panels. Historical briefs without the policy marker remain readable, and the deterministic tools may still read exact four-panel and six-panel legacy episodes for targeted recomposition. Write deterministic findings and a compact active/skipped module summary to `qa-report.md` without discarding an existing Agent QA section, then summarize both agent and script results in chat.

Remove temporary files and staging directories created during the run. Preserve episode artifacts, user reference images, and memory. Stop before any external publishing step unless the user has explicitly approved it.

## Story-quality gate (schema 1.1)

Idea returns exactly 3 rich directions using 2+ humor engines. StoryCritic runs a premise stage, then a script stage, classifying failures as: topic, mechanism, hook, beats, payoff, dialogue, duplicate, safety, or visual; allow at most 2 rewrites. User-supplied topics bypass the scout. Never use profanity or obfuscated profanity; blunt, non-profane Korean is allowed.
