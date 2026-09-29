# Informational workflow — brief 1.2

Use for policy, finance, economy, investing and explanatory news. Humor is optional. This replaces the legacy three-direction, humor-score, premise-critic and separate dialogue/continuity reviews. Preserve explicit topic/layout and all safety, source, reference and final-image safeguards.

## Select, then answer

Topic search uses Aside and five concise candidates: evidence 1.1 → research 1.3. Demand rules live in `keyword-evidence.md`. A fixed topic/revision skips selection and rotation; refresh only material official facts as needed.

Write brief 1.2 with `content_type: informational`. `question_answer` contains `search_keyword`, one `reader_question`, `one_line_answer`, `required_facts`, `reader_action`, `out_of_scope`. Each fact has unique `id`, `claim`, category (`identity`, `relevance`, `benefit`, `condition`, `risk`, `uncertainty`), and official `sources` with `url`, `title`, `publisher`, `checked_on`, short `supporting_excerpt`. Inspect actual support: an official URL alone does not prove a claim.

Plan **one** direction: `id`, `premise`, `hook_promise`, one `development_changes` item per inner panel, `ending_answer`. More directions require `additional_direction_reason` (ambiguity or failed direction). No fake humor engine, twist or score. Address benefits, conditions and risks; explain genuine non-applicability instead of inventing a benefit.

## Write once

Keep script 1.1 and the existing layout contract. The technical beat `ending_payoff` means the answer/next check here, not mandatory reversal. Opening identifies subject and question; each inner panel adds information, resolves an error or changes a decision; ending answers that question. A generic money-management lesson cannot replace product-specific information.

Use short conversational Korean, at most two bubbles per panel, no profanity and the established voice. Visible dialogue must accurately retain material dates, figures, benefit conditions, exclusions and uncertainty; the caption cannot repair missing core information. No universal investment recommendation, guaranteed returns or tax-deduction-as-cash-refund claim.

## One independent content review, two ordered inputs

Give one fresh reviewer **only the script first**, without brief, planned answer or writer justification. Record unaided topic, learned information and next action. Then give that same reviewer the question-answer card, official evidence and relevant character/continuity constraints. Do not add separate premise, dialogue, continuity and comprehension agents.

Persist `content-review.json` using `scripts/content_review.py`:

- schema 1.0, episode ID, distinct actual `writer_id`/`reviewer_id`, SHA-256 of current brief/script bytes;
- `stages: ["blind_read", "card_source_checks"]`;
- `blind_read: {completed_at, topic_understood, learned, next_action}`, then later `checked_at`, both timezone-aware;
- six `checks`, each `{passed, evidence}`: `answers_reader_question`, `topic_specificity`, `claims_sources_conditions`, `benefits_conditions_risks`, `standalone_comprehension`, `dialogue_numbers_continuity`;
- `claim_coverage`: every fact mapped to real `panel`, exact visible `script_quote`, supporting `source_urls`, and `assessment`;
- `review_round` (1–3), `additional_review_reason` after round 1, `outcome: pass|fail`.

All checks and coverage must pass. Unaided understanding must match the card. Include language, safety, benefit/risk balance, figures and character/prop consistency in the same review. Scores cannot override failure. Code validates structure/coverage/freshness, **not semantic truth**. Never forge reviewer independence or pass on file existence alone.

Allow at most two revisions. Recheck affected findings and connected meaning/facts/conclusion; record extra-round reasons. Changed brief/script bytes invalidate the prior review. Failure/missing/stale review stops art. Composition, validation and history call `require_content_review(episode_dir)`; call it before native image generation too.

## Art and final review

Story modules are optional aids. Default information production needs no policy marker/module-routing file. If useful or requested, use the router and its normal record; architecture uses the information direction and shot planning consumes the passed script. No forced payoff exploration.

Resolve references once per generation batch, persist actual paths in prompts and reuse that snapshot. Refresh on new batch, changed references or targeted regeneration; never attach removed files. Character identity wins; use all sorted supported style images, `current/` only when `styles/` is empty. Raw art is text-free; Korean is composed afterward.

Inspect final pages once in reading order for identity, hands/props, continuity, text fit, reading order and mobile readability. Inspect raw panels only for suspected defects. Run cheap deterministic checks after final output. Repair failing panels/pages and affected neighbors only; wording-only edits do not require new art. Do not rerender passing work for subjective polish.

## Handoff and timing

`content-review.json` is the single detailed content review; QA report links/summarizes it and records final visual findings. Search completion uses informational review-state fields in `keyword-evidence.md`; only successful full completion updates history once. Stop at local `review_pending`, never automatic posting.

In QA report or one compact timing record, capture start/end for research, writing, review, generation, composition and final review, plus generation/revision counts. Count overlapping elapsed intervals once. No speedup claim before measurement. Optional two-independent-panel parallel generation requires tool support and measured consistency/speed; no new paid API/account. Use sequential if quality or speed worsens.

First EP-016 improvement pilot stops at passed script for user acceptance. Only afterward generate images and measure a full run. Do not change scheduler or activate the daily default as part of this pilot.
