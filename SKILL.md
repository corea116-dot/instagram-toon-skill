---
name: instagram-toon
description: "Create, revise, compose, and quality-check Korean Instagram comics (인스타툰) entirely inside Codex. Build six story beats as three final images: one strong opening hook, one four-panel development composite, and one ending payoff. When invoked without a topic, research public-web signals and automatically select a safe, source-backed topic; when the user supplies a topic, use it without replacing it. Includes structured scripts, character and style continuity, text-free native or mock panel generation, deterministic Korean speech-bubble composition, legacy 4-cut recomposition, and single-panel regeneration. Use when the user explicitly invokes $instagram-toon or asks in natural language to make, rewrite, regenerate, or QA an 인스타툰, 6컷 만화, Instagram comic, or carousel episode without a separate web app."
---

# Instagram Toon

Act as the episode coordinator. Manage the complete workflow in the current Codex Desktop, CLI, or IDE session; delegate bounded specialist work to native Codex subagents; show progress and QA results in chat; and keep all episode output under the current project's `episodes/` directory. Do not create a web UI.

**Maintenance:** When this skill's behavior or usage changes, update `/Users/b./Documents/인스타툰/INSTAGRAM-TOON-사용설명서.md` in the same change.

## Resolve the request

Read the current request, conversation, project files, and memory before asking questions. Resolve `topic`, `audience`, `tone`, and `characters` in that order.

- First, run `InstagramPostAnalystAgent` only when the current request has an explicit `$instagram-toon` invocation and exactly one direct Instagram post or reel URL. This route takes precedence over a separately written topic; use any extra topic text only as an analysis angle. Load `references/instagram-link-analysis.md`, set `topic_origin` to `instagram_link`, and write `instagram-source.json`. A link-only or implicitly invoked request must not activate this agent. If the public post cannot be read, stop before IdeaAgent and ask for an attachment or short summary; never substitute an unrelated topic.
- When the user supplies a topic with `$instagram-toon` and the Instagram-link route did not activate, set `topic_origin` to `user`, use that topic, and do not run a web search or replace it.
- When the user invokes `$instagram-toon` without a topic, set `topic_origin` to `editorial_scout`, load `references/topic-discovery.md`, and run EditorialScoutAgent before IdeaAgent. EditorialScoutAgent must delegate its evidence-gathering task through an explicit `$ulw-research` invocation, prioritizing normally accessible public Instagram signals and public community discussions. Do not ask for a topic. Its hard editorial gates run before any score; among eligible candidates, it prioritizes cited visible public engagement and then story score. Infer audience, tone, and character from context and memory; use the defaults in `references/topic-discovery.md` when they are absent.
- Run EditorialScoutAgent only during a new episode invocation. Never monitor, search, or choose topics in the background.
- Never ask again for a value already present in the conversation or project.
- Select the next `EP-NNN` identifier from `memory/episode-history.json` and write to `episodes/EP-NNN-kebab-slug/`.

Treat every local result as a draft. Never publish, upload, schedule, send, or otherwise perform an external posting action until the user has reviewed the result and explicitly approved that separate action.

## Choose a mode

- **New episode:** run the complete idea, writing, continuity, art, composition, and QA workflow.
- **Story rewrite:** preserve the topic and fixed user constraints, revise the direction or script, rerun affected story gates, and rebuild art only after the revised story passes.
- **Targeted regeneration:** load the existing episode, revise only the named panel prompt and raw image, then recompose only its affected final image: opening (panel 1), development composite (panels 2–5), or ending (panel 6).
- **Recompose or validate:** preserve story and raw art; run only deterministic composition, validation, and reporting.

## Route story modules

For a new episode or story rewrite, read `references/story-modules/router.md` first. Parse explicit module IDs in the request into `enable` and `disable` overrides, let disable win when the same ID appears in both, apply the router's mode and story signals, and read only the active module files. Never install or run the external GitHub projects cited by the modules.

New episodes created under this policy must set `brief.json.story_module_policy` to `auto_with_overrides` and write `module-routing.json` before IdeaAgent. Record all five modules as active or skipped with a reason and run count. The default new-episode path reads only the router, `story-architecture`, and `storyboard-shot-plan`; optional modules require their documented signal or a user override. Never reload a module during the same draft pass. `recompose`, `validate`, and story-unchanged panel regeneration load zero story modules even if a force-enable request is present. User overrides never disable StoryCritic, safety, language, continuity QA, image, or deterministic validation gates.

## Load only required resources

| Need | Read |
| --- | --- |
| Full workflow or targeted regeneration | `references/workflow.md` |
| New story or story rewrite module selection | `references/story-modules/router.md`, then only its active modules |
| Hierarchical premise and six-beat causality | `references/story-modules/story-architecture.md` when active |
| Serial canon or state-heavy continuity | `references/story-modules/continuity-canon.md` when active |
| Multi-speaker voice separation | `references/story-modules/dialogue-persona.md` when active |
| Mechanism, beats, payoff, or duplicate recovery | `references/story-modules/branch-payoff-lab.md` when active, at most once |
| Story-to-shot conversion | `references/story-modules/storyboard-shot-plan.md` when active |
| Automatic topic discovery | `references/topic-discovery.md`, `$ulw-research`, `memory/brand-bible.md`, `memory/banned-topics.json`, `memory/episode-history.json` |
| Explicit Instagram post or reel link | `references/instagram-link-analysis.md`, `memory/banned-topics.json`, `memory/episode-history.json` |
| Idea, writing, dialogue, or caption work | `references/story-rules.md`, `memory/dialogue-style.md`, `memory/banned-topics.json`, `memory/episode-history.json` |
| Character or scene continuity | `memory/character-bible.json`, `memory/visual-style.json` |
| Art direction or panel regeneration | `references/visual-rules.md`, `memory/brand-bible.md`, character/style memory |
| Dialogue naturalness review | `references/dialogue-naturalness.md`, `memory/dialogue-style.md` |
| Story, continuity, or visual critique | `references/qa-rubric.md` |
| File creation, JSON, prompts, or CLI use | `references/output-schema.md` |

Do not pass the entire skill to each subagent. Give each one only its relevant input JSON, reference paths, output contract, and write boundary.

## Run the coordinated workflow

1. When `topic_origin` is `instagram_link`, ask InstagramPostAnalystAgent to inspect only the linked public post and return `instagram-source.json`. It may abstract the original ending reversal, but must require three changed non-ending dimensions and pass duplicate and safety checks before IdeaAgent.
2. When `topic_origin` is `editorial_scout`, ask EditorialScoutAgent to invoke `$ulw-research` for its evidence-gathering subtask before it returns exactly five source-backed candidates. Prioritize normally accessible public Instagram signals and public community discussions, then use any other public source only as a corroborating or availability fallback. Record only visibly shown public reactions, likes, comments, or upvotes; do not estimate or access hidden metrics. Run its source relevance, contradiction, mechanism, visual-hook, payoff-pressure, safety, and duplicate gates before scoring; preserve failed candidates with reasons, then select the eligible candidate with the strongest cited engagement priority and highest score on a tie. Write `topic-research.json` version 1.1 and continue automatically. If none is eligible, return `requires_user_input` and stop before IdeaAgent.
3. Route story modules, write the policy marker and `module-routing.json`, and read only active module references. Feed `story-architecture` to IdeaAgent/WriterAgent when active.
4. Ask IdeaAgent to return exactly three rich 1.1 directions plus duplicate and sensitivity findings. Each must name a human truth, behavioral contradiction, primary engine and explanation, hook promise, exactly four distinct visible development changes, payoff reversal, and beat signature; use at least two primary engines across the three. Run StoryCriticAgent in premise mode before WriterAgent, then select only a passing direction unless the user requested a choice.
5. Ask WriterAgent to realize the approved direction without replacing its engine, contradiction, or payoff. Return structured JSON with exactly six ordered panels: one scroll-stopping opening hook, four state-changing development beats, and one short ending payoff. The opening must hook through an immediately legible visual, a concise line, or both without spoiling the ending. Allow no more than two dialogue bubbles per panel.
6. Ask ContinuityAgent to return panel-addressed JSON findings against the character, dialogue, style, background, time, position, and prop state bibles. When `continuity-canon` is active, pass only its locked facts, current state, mutable state, and open callbacks. Apply only the named corrections.
7. Ask StoryCriticAgent in script mode to score comprehension, relatability, dialogue brevity, twist effect, and originality from 0 to 20 each, and independently enforce every script hard gate. A pass requires a total of at least 80 and every hard gate; scores never rescue a hard failure. Return a typed `failure_class`, `reroute_to`, hook question, payoff-reframing evidence, and concrete instructions. For `mechanism`, `beats`, `payoff`, or `duplicate`, run an active `branch-payoff-lab` at most once and pass only its selected branch upstream. Permit at most two total script rewrites; never spend them on topic- or mechanism-level failures, and stop before art if the best draft still fails.
8. After story QA passes, apply `dialogue-persona` when active, then ask DialogueNaturalnessAgent for a conservative Korean dialogue review. It may make at most one safe wording revision; it must preserve speaker, bubble count, geometry, facts, timing, twist, intentional fragments, and character voice. If its JSON requests a story recheck, rerun StoryCriticAgent before art.
9. When `storyboard-shot-plan` is active, pass its six panel event/action/expression/prop/camera plan to ArtDirectorAgent. Ask ArtDirectorAgent to lock the complete six-beat storyboard and camera plan before rendering, with the opening composed for immediate mobile-feed impact. For every panel, put every `primary_reference_images` path from `memory/visual-style.json` first in `reference_images` and apply its palette, sparse-background, and mood rules. Use the character and style reference paths from memory with the image-generation capability available to the current Codex surface.
10. Keep every generated raw panel free of letters, Hangul, numbers, captions, subtitles, speech bubbles, UI text, watermarks, signatures, and logos. Store provider inputs in `prompts/panel-N.json` and outputs in `raw/panel-N.png`.
11. Run the deterministic composer to insert Korean dialogue, wrap lines, fit type, place bubbles, and export exactly three final PNGs: `opening.png`, `development-four-panel.png`, and `ending.png`. Retain text-composited per-panel images only under `composed/` for targeted regeneration; do not treat them as postable exports.
12. Ask VisualCriticAgent to return panel number, problem, severity, and revision prompt for character consistency, hands and props, script match, continuity, bubble space, mobile readability, and style. For a primary-reference style failure, regenerate only the failing panel once automatically, then show any remaining issue for review.
13. Run deterministic validation. Update history only after validation succeeds. Summarize topic-selection origin and result, active/skipped story modules and their reasons, story score, dialogue-naturalness status, continuity status, visual findings, output paths, and any unresolved risk in chat.

Treat InstagramPostAnalystAgent, EditorialScoutAgent, IdeaAgent, WriterAgent, ContinuityAgent, DialogueNaturalnessAgent, ArtDirectorAgent, StoryCriticAgent, and VisualCriticAgent as task contracts, not hard-coded runtime agent types. Map them to the native roles available on the current surface as specified in `references/workflow.md`. Keep integration and final file writes with the coordinating agent.

## Use the image-provider boundary

Keep image generation behind this file contract:

```text
prompts/panel-N.json -> current provider -> raw/panel-N.png
```

Use the current Codex image-generation capability first for real art. Use `--mock` for network-free development and testing. Allow a future `scripts/generate_panel.py` OpenAI Image API adapter to consume the same prompt JSON and produce the same raw PNG without changing composition, validation, or history code.

When the user supplies character or style images, place copies under `assets/references/characters/` or `assets/references/styles/` and add their project-relative paths to `memory/character-bible.json` or `memory/visual-style.json`. For the configured primary style references, attach every primary image to every new panel and every user-requested targeted regeneration. Do not batch-regenerate old episodes. Describe observable traits; do not claim training or fine-tuning.

## Run deterministic tools

From the skill root, run:

```bash
uv run scripts/compose_episode.py --episode-dir /absolute/project/episodes/EP-001-title --mock
uv run scripts/validate_episode.py --episode-dir /absolute/project/episodes/EP-001-title
uv run scripts/update_history.py --episode-dir /absolute/project/episodes/EP-001-title --status draft
```

For one failed panel, add `--panel N` to the composer. Do not recreate passing raw panels. Require each successful CLI to print a result path; surface its stderr when it exits nonzero. Remove temporary files created during the run.

Finish only when the required episode files exist, policy-enabled new episodes have a valid `module-routing.json`, automatic selections have a valid `topic-research.json`, Instagram-link selections have a valid `instagram-source.json`, final PNGs are exactly 1080x1350, validation passes, agent QA is recorded in `qa-report.md`, and the result has been shown in chat. Stop at the local draft boundary unless explicit posting approval arrives afterward.

## Story-quality 1.1

For automatic topic selection, run and pass source-relevance, human-observation, behavioral-contradiction, named-humor-engine, hook/payoff-seed, safety, and duplicate gates **before** any score is considered; a score cannot rescue an ineligible candidate. A direct user topic skips EditorialScoutAgent and proceeds as `topic_origin: user`. IdeaAgent must produce exactly three directions using at least two named humor engines. StoryCriticAgent reviews in two stages—premise before drafting and script after drafting—and permits no more than two total rewrites. Require no profanity or obscured/initial-only profanity; rough but non-profane Korean remains permitted when natural to the character and situation.
