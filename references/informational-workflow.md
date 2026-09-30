# Informational workflow 1.3 — question and action first

Use for policy, finance, economy, investing and explanatory news. Humor is optional. This replaces the legacy three-direction, humor-score, premise-critic and separate dialogue/continuity reviews. Preserve explicit topic/layout and all safety, official-source, reference and final-image safeguards. Historical brief 1.2/script 1.1 episodes remain readable; new information episodes use brief 1.3 and script 1.2.

## 1. Select a topic, then make one clear promise

Follow `model-routing.md` for dispatch: Sol/low scout, one continuing Sol/high creator for idea/script/art direction, one independent Astra/high integrated content reviewer, and Sol/medium final visual review. Keep coordinator integration at the project Sol/medium default when available. Do not run the separate humor reviewers or inherit the entire conversation into each agent.

Topic search uses Aside and five concise candidates: evidence 1.1 → research 1.3. Demand rules live in `keyword-evidence.md`. A fixed topic/revision skips selection and rotation; refresh only material official facts as needed.

Before drafting, write one four-part topic contract in brief 1.3:

- exact topic;
- one `reader_question`;
- one `one_line_answer`;
- one to three distinct `reader_actions` that the reader can actually perform.

Keep the existing `reader_action` as a short summary for compatibility. `required_facts` retain unique `id`, `claim`, category (`identity`, `relevance`, `benefit`, `condition`, `risk`, `uncertainty`) and official `sources` with `url`, `title`, `publisher`, `checked_on`, and a short `supporting_excerpt`. Inspect actual support: an official URL alone does not prove a claim. `out_of_scope` states what the episode does not decide.

Plan one direction with `premise`, `hook_promise`, one distinct `development_changes` item per inner panel, and `ending_answer`. More directions require a recorded ambiguity or failed-direction reason. A high-demand keyword does not excuse a vague reader question.

## 2. Give every panel one necessary job

Write script 1.2 with the selected `output_layout`. Every panel records:

- `panel_job`: the question or decision handled by this panel;
- `new_information`: the one new fact or distinction it contributes;
- `reader_takeaway`: what the reader should be able to repeat afterward;
- `scope`: for example all ISA accounts, only a named account type, or one stated case;
- `text_budget`: the maximum visible non-space characters allowed in the panel.

Adjacent panels cannot have the same `panel_job`. Opening states the subject and promised question; each inner panel changes the reader's understanding or decision; ending answers the opening and converts it into the concrete `reader_actions`. A definition panel followed by the same definition in different words fails. A type-specific condition must not become a general conclusion later.

Total panel count is not a substitute for structure. Keep the user's requested layout. Redistribute, shorten or split dense information before adding panels.

### Choose character-led or character-and-card presentation

Default to a character-led scene with expressive action, framing, essential props and dialogue, without an information card. Character-led includes solo action and interactions with other characters; it never requires solo-only staging. Use it for a question, situation, short explanation, distinction or reaction that changes understanding. A character-led panel must still contribute its recorded new information or necessary story transition; do not replace removed card information with empty reactions.

Plan scene construction independently of card choice, using the scene policy in `visual-rules.md`. In existing `scene`, name the on-screen character IDs, place and situation; in `action`, state who acts or responds to whom. Use `background`, `props` and `camera` to describe necessary spatial context, object state, framing and room for text. In the script preview show this scene alongside the dialogue and card reason, not in a separate approval step or new JSON artifact. An episode cast is a roster, not an instruction to draw everyone in every panel. Register any needed supporting character in the existing character bible before executable generation; preserve each identity separately.

Use situation, interaction, structured explanation and concrete action according to the panel's job, without quotas. A scene may use a concise room, a peer checking a phone, or a purposeful close-up; do not add people or furniture merely for variety. A fictional peer must not imply official expertise, personal eligibility, approval or payment. Keep a necessary qualification explicit even when the picture becomes more narrative.

Choose a character-and-card panel only when a table, comparison, multiple conditions or structured sequence makes the information materially easier to understand than speech alone. A single date, number or factual sentence is not sufficient reason to add a card. Preserve all material facts and qualifications regardless of presentation.

In the script preview, label each panel `캐릭터 중심` or `카드+캐릭터` and give a short reason based on its job. In executable script 1.2, absence/null of `information_card` means character-led; presence means character-and-card. Use existing action/camera fields and card design_reason; no new schema field or separate review artifact is necessary.

Plan both modes across a mixed episode, without a quota, fixed ratio or strict alternation. Check consecutive card panels for a real comparison/explanation need and vary character action and framing so the episode does not become identical presenter slides. Do not insert a needless card merely to meet a ratio. Show the chosen sequence alongside dialogue at the existing script preview, not in a new approval stage.

For a chosen card panel, plan **character + explanatory speech bubble + information card in the same panel**. The character points to, compares, checks or reacts to the card; record that interaction and a visible character area. A small decorative avatar disconnected from the explanation does not satisfy this rule. This requirement applies only to card panels, not to every informational explanation.

Choose the card form to match its information: a table for categories and amounts, a calendar for a deadline, contrasting blocks for alternatives, a short sequence for actions, or another clear arrangement. These are examples, not a fixed catalogue or one template reused everywhere. Record why the form helps this panel's job. Design card cells, emphasis and placement per panel; keep palette and character identity consistent.

In card panels, split the approved meaning between speech and card: the bubble asks, interprets or explains what the reader should notice; the card carries details that benefit from that arrangement. In character-led panels, dialogue may directly convey exact dates, numbers and conditions. Do not merely repeat a whole card in the bubble. Keep qualifications adjacent to the numbers they limit; a heading, arrow or spatial grouping must not introduce a false relationship. Do not move essential conditions to the post caption. A card does not expand the total panel text budget.

Reserve separate readable regions for character, card and bubble before art. Preserve the requested page/panel layout; reduce redundant wording or reallocate space instead of shrinking the character to a sticker or the text below the readability limit. If essential content cannot fit, report the specific constraint before changing the requested panel count.

## 3. Write natural Korean with an explicit object and action

Use short conversational Korean, at most two bubbles per panel, and the established character voice. Apply `dialogue-naturalness.md` and `memory/dialogue-style.md` to information as part of the integrated review.

Reject compressed copy that loses its object or action. In this register, prefer `ISA 계좌를 개설하기 전에` or `ISA 계좌를 만들기 전에` over the English-calque-like `열기 전`. Reject generic lines such as `세 가지만 확인해` or `한쪽만 고르면 안 돼` unless the same panel immediately names the three checks or two choices and tells the reader what to do.

Visible dialogue and card text together must retain material dates, figures, benefit conditions, exclusions, uncertainty and applicability. Natural dialogue can explain the significance while the card displays exact details. The caption cannot repair missing core information. No universal investment recommendation, guaranteed return or tax-deduction-as-cash-refund claim.

## 4. Run one integrated content review

Use one fresh reviewer, not additional premise/dialogue/continuity agents. First provide only the script, including all card text, intended grouping and character interaction. The blind reader must record:

- the exact question they believe the episode answered;
- the learned answer;
- the one to three action steps in their own words;
- any panels that repeat another panel;
- any awkward, translated or AI-copy-like phrase;
- where they would check the latest condition next.

Then provide the same reviewer the topic contract, official evidence and relevant character/continuity constraints. Persist `content-review.json` schema 1.1 with `content_sha256` and `layout_sha256`, the two ordered stages, claim coverage and these twelve hard checks:

- `answers_reader_question`
- `topic_specificity`
- `claims_sources_conditions`
- `benefits_conditions_risks`
- `standalone_comprehension`
- `dialogue_numbers_continuity`
- `promise_payoff_alignment`
- `distinct_panel_value`
- `ending_actionability`
- `scope_consistency`
- `korean_naturalness`
- `layout_density`

Every check and required-fact coverage must pass. The blind reader must restate the same number of actions as the brief. A pass cannot retain repeated-panel or awkward-phrase findings. Scores never override a hard failure. Code validates structure, evidence mapping and freshness, not semantic truth.

Under those same twelve checks, inspect whether each card is necessary, character-led panels contribute information rather than filler, and the sequence avoids repetitive presentation. Check whether the planned cast, setting and interaction carry a situation rather than merely changing the presenter's hand pose, and whether any visual implication changes a policy condition. For card panels also inspect bubble/card complementarity, adjacent conditions, unambiguous table labels/units, and whether the character actually explains the card. Required-fact quotes may come from dialogue or card text. Do not add another review agent or a separate scene/card review gate.

Allow at most two content revisions. Recheck only affected findings plus connected facts and conclusion. Do not add more reviewers to compensate for a weak rubric.

## 5. Lock the words before generating art

During calibration, stop after the passed script and show the user only the exact topic, one-line answer, all dialogue and card text with intended form, final action line, and material conditions/limitations. After explicit acceptance, run:

```bash
uv run scripts/lock_content.py \
  --episode-dir /absolute/project/episodes/EP-NNN-title \
  --mode user_accepted \
  --approval-note "사용자가 대본과 마지막 행동 문구를 확인함"
```

This writes `content-lock.json` bound to the semantic content hash. Until the user explicitly adopts this 1.3 baseline for unattended daily production, do not use `automatic_contract`. After that separate adoption, an automatic run may lock a passed contract with `automatic_contract` and continue to local `review_pending`; this never authorizes posting.

Any topic, fact, panel job, scope, speaker, dialogue or card wording/meaning change invalidates both review and lock. Moving exact words from speech to a card still changes presentation and requires an affected-content check; do not assume an earlier dialogue-only review covers it. Geometry-only bubble/card/character-area changes do not invalidate semantic review, but do invalidate layout preflight. Reuse still-current official evidence; do not repeat topic search for a presentation change.

## 6. Preflight the final page layout before art

After content lock and before provider prompts or image generation, run:

```bash
uv run scripts/layout_preflight.py \
  --episode-dir /absolute/project/episodes/EP-NNN-title
```

The preflight uses the real Korean font fitting and final page-group scale for both bubbles and all card text blocks. It fails when effective text is below 34 px, combined text exceeds the panel's `text_budget`, reserved regions overlap, or a three/four-panel page contains more than one text-heavy panel. Fix redundant wording or safe areas and rerun only this check; changing the user's page grouping requires permission. Do not generate art while `layout-preflight.json` is missing, failed or stale.

## 7. Generate art and review once

Only after current content review, content lock and layout preflight pass may art begin. Resolve references once per generation batch, persist actual paths in prompts and reuse that snapshot. Character identity wins; use all sorted supported style images, falling back to `current/` only when `styles/` is empty. Raw art remains text-free; deterministic composition inserts Korean afterward.

For character-led panels, render the planned on-screen cast, meaningful action and setting; reserve only needed dialogue space, not an empty card rectangle. Apply the scene policy in `visual-rules.md`; do not replace a planned interaction with a solitary presenter or remove a necessary setting to make the paper blank. For a card panel, prompt a substantial, recognizable character in the reserved area interacting with the planned card, and leave the card/bubble areas free of important art. The compositor draws the designed card and all its Korean text, not the image model. Avoid painting a second card into the raw illustration. Card styling may vary with its purpose while staying within the episode palette.

Inspect final pages once in reading order for identity, hands/props, continuity, text fit, reading order and mobile readability. Each card panel must visibly include the explaining character and bubble; reject card-only output, a token character sticker, a hidden face, unrelated gestures, or a table/arrow whose visual grouping changes the meaning. Declared character boxes are planning data, not proof that the generated art obeyed them. Inspect raw panels only for suspected defects. Repair failing panels/pages and affected neighbors only. Wording-only edits do not require new art, but they do require renewed content review, lock and layout preflight.

## 8. Handoff, hashes and timing

`content-review.json` is the single detailed content review; `content-lock.json` records the approved semantic version; `layout-preflight.json` records the current geometry/page grouping. `qa-report.md` links or summarizes them and records final visual findings.

`content_sha256` covers the brief's meaning and the script's story/visible words including card content and explanatory interaction, without placement geometry. `layout_sha256` covers output grouping, visible text, text budget and bubble/card/character geometry. A geometry-only edit reruns layout/visual checks, not official-source/content review.

Capture one compact timing record for research, writing, review, preflight, generation, composition and final review, plus content/visual/generation revision counts. Count overlapping intervals once. Do not claim speed improvement before at least three comparable 1.3 pilot runs. Stop at local `review_pending`; never post automatically.
