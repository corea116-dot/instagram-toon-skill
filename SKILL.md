---
name: instagram-toon
description: "Search for source-backed Korean Instagram comic topics using Aside and Naver/Google keyword demand, or create, revise, compose, and quality-check an 인스타툰 entirely inside Codex. Topic search targets 20–30대 사회초년생 and alternates timely and evergreen demand; an explicit user topic is never replaced. Build user-requested output groups, defaulting to five single-panel final images, with structured scripts, character/style continuity, text-free art, deterministic Korean dialogue composition, and QA. Use when the user invokes $instagram-toon or asks to search/select an 인스타툰 topic, make a comic, rewrite, regenerate, or QA an Instagram comic or carousel episode, or adapt a finished episode into motion graphics using its original artwork as reference."
---

# Instagram Toon

Act as the episode coordinator. Manage the complete workflow in the current Codex Desktop, CLI, or IDE session; delegate bounded specialist work to native Codex subagents; show progress and QA results in chat; and keep all episode output under the current project's `episodes/` directory. Do not create a web UI.

**Maintenance:** When this skill's behavior or usage changes, update the repository's `INSTAGRAM-TOON-사용설명서.md` in the same change. Also synchronize the active project's copy when it exists; in the original workspace it is `/Users/b./Documents/인스타툰/INSTAGRAM-TOON-사용설명서.md`.

**Model routing:** Before delegating, read `references/model-routing.md`. Use the project-registered `toon_*` roles: GPT-6.1 Sol for coordination/collection/creation/visual review, GPT-6 Astra high for the independent informational content review. No GPT-5.6 or older Sol. For comics, keep idea, script and art direction in one continuing creator. Motion uses a separate Astra low planner and GPT-6.1 Sol high producer. Verify actual runtime settings; existing chat overrides may differ from project defaults.

**Naver monthly periods:** A provider label such as `최근 한달간` plus the observation timestamp is sufficient; do not require or invent exact start/end dates. See `references/keyword-evidence.md` for the comparable-snapshot contract.

## Existing-episode motion route

When the user requests a motion graphic/video from a finished comic, or revises that video, read `references/motion-workflow.md` and follow it instead of new-comic production below. Dispatch `toon_motion_planner` (GPT-6 Astra low, astra-light) for scenes and direction, then `toon_motion_producer` (GPT-6.1 Sol high) for execution after script review. Use the actual episode as source, generate appropriate new motion artwork from those references, then produce timed character action, voice, music, effects and video QA. Keep the source comic unchanged. This route does not select a new topic, allocate another episode ID or advance topic rotation. Ordinary comic requests do not automatically include video.

## Content type first

Policy, finance, economy, investing and explanatory news use `references/informational-workflow.md`: topic promise → panel jobs → script → one integrated content review → content lock → layout preflight → art → final QA. Read it for this route; it replaces the humor-specific multi-agent procedure below, not safety, sources, character/style or deterministic gates. Keep everyday humor on the existing route. During calibration, show the reviewed script before images unless the user explicitly requests an end-to-end finished episode in the current run. Record that one-run authorization as `user_authorized_run`; it is not acceptance of unattended future runs. Unattended daily continuation still requires separate baseline acceptance.

**Scene-led mixed presentation:** Character-led does not mean solo-only. Plan who is present, where they are, and what visible action or interaction carries each panel; use supporting characters and concise settings when they help. Select a card only when its visual structure materially helps understanding, without a fixed ratio or alternating pattern. When a card is used, a visible character explains it in the same panel. Show the scene and card choice together in the existing script preview. See `references/visual-rules.md` for scene/reference policy and the information workflow for review, lock and text fit.

## Resolve the request

Read the current request, conversation, project files, and memory before asking questions. Resolve `topic`, `audience`, `tone`, `characters`, and `output_layout` in that order.

- Parse an explicit output expression such as `2컷+3컷` or `1컷짜리 5장` into ordered page sizes. Each page may contain one to four panels, and the sum is the story panel count.
- Without an explicit output expression, use `output_layout: [1, 1, 1, 1, 1]`: a five-panel story exported as five single-panel images.
- New scripts set `rendering_policy: "frame_native_v1"`. Plan art and every overlay in the actual slot pixels from `output_layout` (see output schema); fill the frame and crop raw art before text. Omitted policy retains historical rendering.
- Store `output_layout` in brief and script: new information uses brief 1.3/script 1.2; humor keeps brief/script 1.1. Historical information brief 1.2/script 1.1 remains readable. Use opening, information-changing development and ending action for information, payoff for humor. Reject invalid page sizes before drafting.

- First, run `InstagramPostAnalystAgent` only when the current request has an explicit `$instagram-toon` invocation and exactly one direct Instagram post or reel URL. This route takes precedence over a separately written topic; use any extra topic text only as an analysis angle. Load `references/instagram-link-analysis.md`, set `topic_origin` to `instagram_link`, and write `instagram-source.json`. A link-only or implicitly invoked request must not activate this agent. If the public post cannot be read, stop before IdeaAgent and ask for an attachment or short summary; never substitute an unrelated topic.
- When the user supplies a topic and the Instagram-link route did not activate, set `topic_origin` to `user` and do not search for a replacement. Verify official facts about that fixed topic when accuracy matters.
- For topic search/new episodes without a fixed topic, use `topic_origin: editorial_scout` and read `topic-discovery.md` plus `keyword-evidence.md`. Broad categories are filters, not fixed topics. Aside collects Naver/Google evidence; local `topic_search.py` selects research 1.3 for information or 1.2 for humor. Preserve the relevant gates; no `$ulw-research` requirement or invented fallback.
- Run EditorialScoutAgent only within an explicitly requested topic-search or new-episode run, including a separately authorized scheduled run. This skill does not create a scheduler or start background monitoring.
- Never ask again for a value already present in the conversation or project.
- For a full new episode, select the next `EP-NNN` identifier from `memory/episode-history.json` and write to `episodes/EP-NNN-kebab-slug/`.

Treat every local result as a draft. Never publish, upload, schedule, send, or otherwise perform an external posting action until the user has reviewed the result and explicitly approved that separate action.

## Choose a mode

- **Existing-episode motion graphics:** adapt or revise a video under the source episode using `references/motion-workflow.md`; apply its specialized pipeline, not the comic creation steps.

- **Topic search only:** requests such as `$instagram-toon 주제 검색만 해줘` produce the five-candidate evidence and `topic-research.json` containing a ranked selection or hold. If collection cannot supply five real candidates, preserve the partial evidence and a hold diagnosis instead. Stop before story modules, IdeaAgent, script, and images; do not update episode history or consume a rotation turn.
- **New episode:** run the complete idea, writing, continuity, art, composition, and QA workflow.
- **Story rewrite:** preserve the topic and fixed user constraints, revise the direction or script, rerun affected story gates, and rebuild art only after the revised story passes.
- **Targeted regeneration:** load the existing episode, revise only the named panel prompt and raw image, then recompose only the final page that contains that panel.
- **Recompose or validate:** preserve story and raw art; run only deterministic composition, validation, and reporting.

**Speech-bubble appearance (all content types and layouts):** Use the common `scripts/rendering.py` compositor: merge the rounded body and tail into one filled shape and draw only its outer outline. The body-to-tail join must remain open, with no internal horizontal border. Apply the composition and final-review checks in `references/visual-rules.md`.

**Information card design:** For a newly planned information card, use the user-selected #01 taped memo skin: set `information_card.style: "taped_memo_v1"` and read `references/information-card-style.md`. It also governs new motion information overlays. Keep content-specific grouping and the explaining character; this design choice does not force a card into every scene. Absent style preserves historical cards.

## Route story modules (humor; optional for information)

For a new episode or story rewrite, read `references/story-modules/router.md` first. Parse explicit module IDs in the request into `enable` and `disable` overrides, let disable win when the same ID appears in both, apply the router's mode and story signals, and read only the active module files. Never install or run the external GitHub projects cited by the modules.

New episodes created under this policy must set `brief.json.story_module_policy` to `auto_with_overrides` and write `module-routing.json` before IdeaAgent. Record all five modules as active or skipped with a reason and run count. The default new-episode path reads only the router, `story-architecture`, and `storyboard-shot-plan`; optional modules require their documented signal or a user override. Never reload a module during the same draft pass. `recompose`, `validate`, and story-unchanged panel regeneration load zero story modules even if a force-enable request is present. User overrides never disable StoryCritic, safety, language, continuity QA, image, or deterministic validation gates.

## Load only required resources

| Need | Read |
| --- | --- |
| Existing comic to motion graphics, or motion/audio revision | `references/motion-workflow.md`, `references/model-routing.md` |
| Full workflow or targeted regeneration | `references/workflow.md` |
| New story or story rewrite module selection | `references/story-modules/router.md`, then only its active modules |
| Hierarchical premise and layout-driven causality | `references/story-modules/story-architecture.md` when active |
| Serial canon or state-heavy continuity | `references/story-modules/continuity-canon.md` when active |
| Multi-speaker voice separation | `references/story-modules/dialogue-persona.md` when active |
| Mechanism, beats, payoff, or duplicate recovery | `references/story-modules/branch-payoff-lab.md` when active, at most once |
| Story-to-shot conversion | `references/story-modules/storyboard-shot-plan.md` when active |
| Automatic topic search or search-only | `references/topic-discovery.md`, `references/keyword-evidence.md`, `aside-browser` and its current `aside guide`, `memory/brand-bible.md`, `memory/banned-topics.json`, `memory/episode-history.json` |
| Explicit Instagram post or reel link | `references/instagram-link-analysis.md`, `memory/banned-topics.json`, `memory/episode-history.json` |
| Idea, writing, dialogue, or caption work | `references/story-rules.md`, `memory/dialogue-style.md`, `memory/banned-topics.json`, `memory/episode-history.json` |
| Character or scene continuity | `memory/character-bible.json`, `memory/visual-style.json` |
| Art direction or panel regeneration | `references/visual-rules.md`, `memory/brand-bible.md`, character/style memory |
| Dialogue naturalness review | `references/dialogue-naturalness.md`, `memory/dialogue-style.md` |
| Story, continuity, or visual critique | `references/qa-rubric.md` |
| File creation, JSON, prompts, or CLI use | `references/output-schema.md` |

Do not pass the entire skill to each subagent. Give each one only its relevant input JSON, reference paths, output contract, and write boundary.

## Run the coordinated workflow

For information, follow `references/informational-workflow.md` instead of the numbered humor procedure below. Search uses evidence 1.1/research 1.3 with explicit `editorial_v1` policy; read `references/topic-editorial.md` for discovery provenance, compact judgments and optional supplied-insights summaries. Detailed research stays at five candidates and full writing at one selected direction. Brief 1.3 holds the question, answer and concrete actions; script 1.2 records each panel's job, new information, takeaway, scope and text budget. Before art, require current `content-review.json`, `content-lock.json` and `layout-preflight.json`. CLI schema defaults to information; use `schema --content-type humor` for legacy search.

### Humor procedure (existing schemas)

1. When `topic_origin` is `instagram_link`, ask InstagramPostAnalystAgent to inspect only the linked public post and return `instagram-source.json`. It may abstract the original ending reversal, but must require three changed non-ending dimensions and pass duplicate and safety checks before IdeaAgent.
2. For `editorial_scout`, run `topic_search.py plan`, collect evidence with Aside, and run `topic_search.py select` per `references/topic-discovery.md`. Compare five candidates for 20–30대 사회초년생 across policy/finance/economy/investing, targeting 조회·신규유입. Alternate `trending`/`evergreen` only after successful automatic-episode completion. New information requires `selection_policy: editorial_v1`: use the source-backed lightweight pool and explicit editorial/demand ordering in `references/topic-editorial.md`. Humor uses `naver_monthly` and ranks eligible candidates by Naver monthly PC + mobile searches. Google Trends is auxiliary momentum evidence, never weighted volume. Missing monthly data means hold, not proxy fallback. Retain components, definitions, dates, sources, rejection and type-fallback reasons in information research 1.3 or humor research 1.2. Historical records retain their rules. Hold, collection failure and search-only success stop before IdeaAgent without changing history. Otherwise continue with the selected topic without another topic interview.
3. Route story modules, write the policy marker and `module-routing.json`, and read only active module references. Feed `story-architecture` to IdeaAgent/WriterAgent when active.
4. Ask IdeaAgent to return exactly three rich 1.1 directions plus duplicate and sensitivity findings. Each must name a human truth, behavioral contradiction, primary engine and explanation, hook promise, one distinct visible development change per selected middle panel, payoff reversal, and beat signature; use at least two primary engines across the three. Run StoryCriticAgent in premise mode before WriterAgent, then select only a passing direction unless the user requested a choice.
5. Ask WriterAgent to realize the approved direction without replacing its engine, contradiction, or payoff. Return schema 1.1 `script.json` with the selected number of ordered panels: one scroll-stopping opening hook, state-changing development beats, and one short ending payoff. Include the selected `output_layout`; its sum must equal panel count. The opening must hook through an immediately legible visual, a concise line, or both without spoiling the ending. Allow no more than two dialogue bubbles per panel.
6. Ask ContinuityAgent to return panel-addressed JSON findings against the character, dialogue, style, background, time, position, and prop state bibles. When `continuity-canon` is active, pass only its locked facts, current state, mutable state, and open callbacks. Apply only the named corrections.
7. Ask StoryCriticAgent in script mode to score comprehension, relatability, dialogue brevity, twist effect, and originality from 0 to 20 each, and independently enforce every script hard gate. A pass requires a total of at least 80 and every hard gate; scores never rescue a hard failure. Return a typed `failure_class`, `reroute_to`, hook question, payoff-reframing evidence, and concrete instructions. For `mechanism`, `beats`, `payoff`, or `duplicate`, run an active `branch-payoff-lab` at most once and pass only its selected branch upstream. Permit at most two total script rewrites; never spend them on topic- or mechanism-level failures, and stop before art if the best draft still fails.
8. After story QA passes, apply `dialogue-persona` when active, then ask DialogueNaturalnessAgent for a conservative Korean dialogue review. It may make at most one safe wording revision; it must preserve speaker, bubble count, geometry, facts, timing, twist, intentional fragments, and character voice. If its JSON requests a story recheck, rerun StoryCriticAgent before art.
9. When `storyboard-shot-plan` is active, pass its selected-length panel event/action/expression/prop/camera plan to ArtDirectorAgent. Ask ArtDirectorAgent to lock the complete storyboard and camera plan before rendering, with the opening composed for immediate mobile-feed impact. Immediately before making provider prompts, run `uv run scripts/active_reference.py` from the skill root. Use every path in its `reference_images` array for the prompt manifest and the corresponding `absolute_paths` for provider attachment, not both arrays as separate image sets. Never send the directory marker or an old hardcoded filename to the image provider. For every panel, put the episode characters' resolved authoritative references first in `reference_images`, then all resolved primary style references; deduplicate shared paths. Character identity always wins over style. Apply style only to palette, story-relevant settings, texture, mood, and composition. Use a `wardrobe_overrides` entry only when the script states a story reason; otherwise preserve the character bible's default clothing and footwear.
10. Keep every generated raw panel free of letters, Hangul, numbers, captions, subtitles, speech bubbles, UI text, watermarks, signatures, and logos. Store provider inputs in `prompts/panel-N.json` and outputs in `raw/panel-N.png`.
11. Run the deterministic composer to insert Korean dialogue, wrap lines, fit type, place bubbles, and export `final/page-01.png`, `page-02.png`, and so on for each selected output group. Retain text-composited per-panel images only under `composed/` for targeted regeneration; do not treat them as postable exports. Existing schema 1.0 episodes retain their legacy final file names.
12. Ask VisualCriticAgent to return panel number, problem, severity, and revision prompt in this order: character identity, script and wardrobe continuity, hands and props, bubble space, mobile readability, then style. Face, hair, beard, skin tone, body proportions, and expression-grammar drift are blocking even when the style is otherwise correct. For a primary-reference style failure, regenerate only the failing panel once automatically, then show any remaining issue for review.
13. Run deterministic validation. Update history only after validation and required agent QA succeed; for a search-selected episode, this records one successful automatic completion and advances the next requested keyword type once. Keep the episode a local draft at `review_pending` (검수 대기), not approved or published. Summarize topic-selection origin and evidence strength, active/skipped story modules and their reasons, story score, dialogue-naturalness status, continuity status, visual findings, output paths, and any unresolved risk in chat.

Treat InstagramPostAnalystAgent, EditorialScoutAgent, IdeaAgent, WriterAgent, ContinuityAgent, DialogueNaturalnessAgent, ArtDirectorAgent, StoryCriticAgent, and VisualCriticAgent as task contracts, not hard-coded runtime agent types. Map them to the native roles available on the current surface as specified in `references/workflow.md`. Keep integration and final file writes with the coordinating agent.

## Use the image-provider boundary

Keep image generation behind this file contract:

```text
prompts/panel-N.json -> current provider -> raw/panel-N.png
```

Use the current Codex image-generation capability first for real art. Use `--mock` for network-free development and testing. Allow a future `scripts/generate_panel.py` OpenAI Image API adapter to consume the same prompt JSON and produce the same raw PNG without changing composition, validation, or history code.

For shared references, add/replace images directly in `assets/references/styles/`, without JSON edits. Resolve every non-hidden PNG/JPG/JPEG/WebP in filename order once per generation batch; attach the same full snapshot to each panel. Refresh for new batches, reference changes and targeted regeneration. When empty, use all supported `current/` images instead; never mix them into populated `styles/`. Character/style memory uses the directory marker, not fixed filenames. Run `uv run scripts/active_reference.py` for exact paths. Character-only references remain explicit registered paths. Never reattach removed files or batch-regenerate old episodes. Describe observable traits; do not claim training/fine-tuning.

## Efficient production

For full informational production or revisions, read `references/efficient-production.md`. Use role-specific lossless views and local commands instead of rewriting JSON in chat. Preserve independent semantic and visual judgments.

## Run deterministic tools

From the skill root, run:

```bash
uv run scripts/topic_search.py plan --history memory/episode-history.json
uv run scripts/topic_search.py schema --output /absolute/project/keyword-evidence.schema.json
uv run scripts/topic_search.py select --evidence /absolute/project/keyword-evidence.json --output /absolute/project/topic-research.json --history memory/episode-history.json
uv run scripts/lock_content.py --episode-dir /absolute/project/episodes/EP-001-title --mode user_accepted --approval-note "대본 확인 완료"
uv run scripts/layout_preflight.py --episode-dir /absolute/project/episodes/EP-001-title
uv run scripts/compose_episode.py --episode-dir /absolute/project/episodes/EP-001-title --mock
uv run scripts/validate_episode.py --episode-dir /absolute/project/episodes/EP-001-title
uv run scripts/update_history.py --episode-dir /absolute/project/episodes/EP-001-title --status draft
```

For layout-only changes, use `--recompose-only` (and `--panel N` for one affected panel) to preserve actual generation manifests. For one failed raw panel, update its provider manifest explicitly before regeneration, then recompose. Do not recreate passing raw panels. Require each successful CLI to print a result path; surface its stderr when it exits nonzero. Remove temporary files created during the run.

For search-only, finish after showing the selected topic or explicit hold and its evidence paths; do not require episode files. For full generation, finish only when the required episode files exist, new information has current review/lock/preflight records, policy-enabled new episodes have a valid `module-routing.json`, automatic selections have a valid `topic-research.json`, Instagram-link selections have a valid `instagram-source.json`, every requested final page is exactly 1080x1350, validation passes, agent QA is recorded in `qa-report.md`, and the result has been shown in chat. Stop at the local draft review boundary unless explicit posting approval arrives afterward.

## Story-quality 1.1 (humor only)

For automatic topic selection, run and pass source-relevance, human-observation, behavioral-contradiction, named-humor-engine, hook/payoff-seed, safety, and duplicate gates **before** any score is considered; a score cannot rescue an ineligible candidate. A direct user topic skips EditorialScoutAgent and proceeds as `topic_origin: user`. IdeaAgent must produce exactly three directions using at least two named humor engines. StoryCriticAgent reviews in two stages—premise before drafting and script after drafting—and permits no more than two total rewrites. Require no profanity or obscured/initial-only profanity; rough but non-profane Korean remains permitted when natural to the character and situation.
