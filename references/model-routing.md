# Instagram Toon model routing

Use this policy before delegating an episode task. It supersedes generic native-role suggestions in workflow.md, not user choices or content/visual gates. Do not use GPT-5.6 variants or older Sol models. Sol means exactly `gpt-6.1-sol`.

The active project configuration is `<project>/.codex/config.toml`; its `agents/toon-*.toml` config layers hold the executable model/effort values. This repository includes those role definitions under `.codex/`; merge them into the working project without replacing unrelated settings. The original workspace uses `/Users/b./Documents/인스타툰/.codex/config.toml`. Do not modify global default agents to implement this policy.

| Contract | Native agent role | Model | Effort |
| --- | --- | --- | --- |
| Coordinator | Main chat, project default | gpt-6.1-sol | medium |
| EditorialScoutAgent | toon_scout | gpt-6.1-sol | low |
| IdeaAgent, WriterAgent, ArtDirectorAgent | toon_creator, same continuing agent | gpt-6.1-sol | high |
| Motion scene and direction planner | toon_motion_planner | gpt-6-astra | low (user: astra-light) |
| Motion production executor | toon_motion_producer | gpt-6.1-sol | high |
| Integrated informational content reviewer | toon_content_review, independent of creator | gpt-6-astra | high |
| VisualCriticAgent | toon_visual_review | gpt-6.1-sol | medium |
| InstagramPostAnalystAgent, only for the explicit link route | toon_post_analyst | gpt-6.1-sol | medium |
| Humor StoryCriticAgent, independent of creator | toon_humor_review | gpt-6.1-sol | high |
| Humor DialogueNaturalnessAgent / ContinuityAgent | toon_language_continuity | gpt-6.1-sol | medium |

Image generation uses the existing native image tool, not these text-model settings. Ranking, composition and deterministic validation remain local programs. Do not invent an image-model name or reasoning setting.

## Dispatch and verification

Use the registered `toon_*` role, not an unqualified `default` role with an assumed model. These task contracts authorize their configured model/effort selection for an authorized episode run. Start a delegated task with `fork_turns: "none"` and a bounded handoff; continue that agent for dependent work. Information uses one creator across idea/script/art direction and one independent integrated content reviewer, not all humor reviewers. Independent tasks may overlap; dependent drafting, review and art remain ordered.

Role layers can pin model/effort. Do not assume a spawn override on another fixed role works. If a registered role is unavailable on the current surface, use an override-capable role with the exact model and effort and a bounded context, only when supported. Otherwise report that the routing cannot be enforced; never silently fall back to Astra/high or a forbidden model. An explicit user model choice takes precedence and must be recorded as an override.

Project configuration does not change the current running chat or already-created agents. Use a fresh project session when necessary to load new roles; do not interrupt existing work. If the main chat retains another model, disclose it rather than claiming Sol/medium is active. Never launch a second coordinator just to mask that mismatch.

In the existing QA report record each used contract, agent identity, requested model/effort, and observed model/effort from available runtime metadata or turn logs. Mark unobserved values `unverified`; configuration and successful spawn alone are not runtime proof. Read only relevant metadata, not unrelated conversations or credentials. A mismatched observed model is a routing defect to resolve before further delegation.

## Bounded inputs and outputs

- Scout: candidate/domain constraints, the keyword-evidence contract, and necessary current account/browser context. Return measured counts, provider period, source URLs, observation time and missing fields. The local selector determines the winner.
- Creator: for new automatic information, first one bounded pass over the five shortlisted candidates to supply four-line directions and three explained 0–2 judgments per `topic-editorial.md`; no full scripts yet. After the local selector, continue the same creator with only the selected fixed topic/question/actions, official fact excerpts with URLs, chosen layout, relevant dialogue/character/style constraints and active reference paths. Do not send the entire chat, previous failed drafts or every skill file. Reuse the same creator for art direction after content acceptance; preserve all material explanations and conditions. Token limits must not erase meaningful scenes, supporting characters or useful backgrounds from the approved direction.
- Integrated reviewer: first only the full visible script/card text and intended grouping; then the topic contract, official evidence and relevant continuity rules, in the existing two-stage review. Do not leak the intended answer into the blind stage. Return required review fields plus panel-addressed failures and corrections; omit repetitive praise, not required evidence.
- Visual reviewer: ordered final pages, approved script/layout, relevant identity/style references and checks. Inspect raw art only for a suspected defect. Return findings and affected panels, not a second full description of every page.
- Reuse current sources and accepted artifacts. Recheck changed findings and connected claims/conclusions only. Geometry-only changes rerun layout/visual checks, not topic selection or source research. Keep one canonical structured draft plus the required user preview; do not create extra prose reports.

## Escalation and measurement

For a browser-handling failure, retry only the unresolved collection with `toon_scout_retry` (Sol/medium). Authentication barriers or absent evidence require the corresponding workflow action, not more reasoning. For an ambiguous visual finding, use `toon_visual_retry` (Sol/high) on that finding only. These replace the failed check; they are not routine extra reviewers. Do not repeatedly escalate or default to xhigh/max. Preserve the existing content-revision and image-repair limits.

For the next three comparable authorized episodes, extend the existing QA/timing record with observed input/output/reasoning/cached token usage when available, elapsed time, content revision count, image regeneration count and user feedback. Include coordinator and subagent calls and retries. Do not add reasoning to output totals or cached input to input totals when already included. Missing usage is unknown, not zero. Do not generate extra test episodes or claim a saving percentage without measurements; token counts, API prices and subscription usage are different quantities.

## File handoffs

Use `efficient-production.md` for compact packets and sequential blind/source review in one continuing task. Creator owns assigned staging draft files; reviewer owns only its review records. Coordinator validates and promotes files, never rewrites the full outputs in chat. Keep role models and effort unchanged. Await task completion instead of repeated status queries; provide progress while doing independent work.

## Motion adaptation mapping

For `motion-workflow.md`, explicitly dispatch separate planning and production agents. The user's `astra-light` is mapped to the available `gpt-6-astra` with reasoning effort `low`; it is not a literal model ID. Production uses exactly `gpt-6.1-sol` with `high`. These project-local roles do not change ordinary comic creation or global defaults.

| Responsibility | Owner |
| --- | --- |
| Scene adaptation, hook/payoff, timed dialogue, interaction poses, camera, sound cues and art direction | `toon_motion_planner` — Astra low |
| Referenced motion asset generation, local TTS, music/SFX mix, animation code, rendering and technical checks | `toon_motion_producer` — GPT-6.1 Sol high |
| Independent adapted informational script and fact review | `toon_content_review`, blind read then source check |
| Independent adapted humor story review | `toon_humor_review` instead of informational review |
| Final rendered frame identity, continuity and mobile readability | `toon_visual_review` |
| Source selection, bounded handoffs, review integration, promotion of final files and user delivery | Coordinator |

Call the planner first with source pages/script, current decisions and output constraints. It owns only assigned motion planning drafts (brief, timeline and asset direction), not the source comic or rendering code. After required independent script review passes, call the producer with the reviewed timeline, source references, asset brief and exact version directory. The producer owns assets, code, audio, rendered files and technical evidence in that directory; it must not silently rewrite reviewed claims or the story. Return necessary story changes to the planner and affected content review before further production. Continue the same planner/producer for revisions instead of spawning a new agent per clip or image.

Tell both workers they share the codebase, must preserve others' edits and must stay within their assigned files. The coordinator validates and promotes their output; image tools, local TTS and rendering remain tools used by the production agent, not separate model identities. If a tool is unavailable to the producer, the coordinator may execute its exact bounded request and return the receipt while production ownership remains with the producer.

For unchanged-plan revisions such as voice-only replacement, dispatch the producer directly and reuse accepted planning/content review; rerun affected pronunciation, timing and mix checks. Do not force a new planner or scout. Give reviewers the adaptation timeline and source references. The visual reviewer states whether it inspected frames or playback; ASR cannot replace listening.

Apply the existing runtime verification and bounded handoff rules. If these newly configured roles are not loaded in the current session, use an override-capable role with the exact model/effort only when supported; otherwise report the need for a fresh session rather than pretending the role ran or substituting another model.
