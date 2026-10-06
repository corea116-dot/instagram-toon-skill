# Efficient production without weaker review

Use one canonical draft and derive views; retain all mandatory facts, scene intent, references and independent checks. Never shorten visible content merely to meet a token target.

## Ownership and compact handoffs

Creator writes brief/script/caption into its assigned staging directory and returns paths plus unresolved decisions. Coordinator validates/promotes the files, preserving approved originals. Do not return the same JSON in chat. Keep one creator for drafting and art direction; do not rewrite already explicit direction after acceptance. New facts or changed semantic decisions still need affected review.

Run `production_tools.py packet --episode-dir EP` to emit a lossless `review-visible.txt`, user preview, input hashes and **draft-only** layout diagnostic. It omits the author's intended answer from the blind view. Fix fit errors before semantic review. Draft diagnostics cannot authorize images.

Give the independent reviewer only `review-visible.txt`, relevant character/voice rules and these instructions:
1. Read visible content and record the schema 1.1 blind-read fields in `blind-read.json` before accessing author intent or facts.
2. In the same continuing task, run `production_tools.py sources --episode-dir EP`. It checks the recorded blind read and current input hashes before printing the topic/official-source contract. Check supporting official passages, not just URLs.
3. Write the single `content-review.json` containing all required checks and claim coverage; return its path and actionable failures only. Do not reprint it to the coordinator.

For revisions, send the exact changed panels plus connected facts/conclusion; retain the previous review. Reviewer patches affected fields in its existing record, updates current hashes/round/reason and reruns the review validator. It must not refresh a hash as a substitute for reviewing changed meaning. Do not run another blind first-read after the same reviewer knows the intended answer; preserve initial reading and document corrected findings honestly.

Run `lock_content.py` with the authorization mode that actually applies, then the standard `layout_preflight.py`. Explicit one-run end-to-end authorization uses `user_authorized_run`, never a fabricated claim that the user approved unseen wording. This does not change the baseline for future runs.

## Generation and rendering

Run `production_tools.py prepare-prompts --episode-dir EP` after gates pass. It resolves the full reference snapshot once and emits manifests without requiring placeholder raw images. Existing manifests cause a stop to avoid overwriting real provider inputs.

Use the native image tool with the exact recorded prompt, safe areas, negative prompt and full reference paths. If provider instructions need creative changes, save them to the manifest before calling. Keep the actual prompt stable throughout generation. Record actual wall-clock start/end around each call, not reconstructed timestamps.

`production_tools.py record-image --episode-dir EP --panel N --source ABS --started ISO --completed ISO` normalizes delivery dimensions, saves raw output and logs actual manifest hash/provider output. It refuses a duplicate panel/revision record. A real retry uses a new revision and preserves prior provider output.

`compose_episode.py --episode-dir EP --recompose-only` inserts text/cards without changing prompts or raw art. Add `--panel N` only when a complete composition exists. Layout-only edits must use this mode. Legacy compose/mock behavior remains for compatibility.

Use optional `dialogue.tail_anchor` for multiple speakers; put bubbles above their speaker and keep important hands/faces outside overlay regions. Confirm actual art in final visual review: declared coordinates alone do not prove it followed the plan.

## Final review and local handoff

Visual reviewer inspects every final page once in order; only defects need raw-art inspection. Persist `visual-review.json` with:
- `overall: pass|fail`, `reviewer_id`, `findings`;
- `reviewed_pages`: ordered relative `final/page-NN.png` paths;
- `page_sha256`: actual SHA-256 for every inspected final page;
- current `content_sha256` and `layout_sha256`.

On repair, recheck affected pages/neighbors; retain unchanged page hashes and original coverage. The final record still covers all pages. Never manufacture PASS or remove an unresolved finding to satisfy the helper.

`production_tools.py finalize --episode-dir EP --history ABS` validates current independent reviews/hashes, runs deterministic validation, creates the strict review state, summarizes Agent QA, writes draft history and exports a PNG+caption ZIP. A missing/failed/stale review stops before history changes. It never uploads or publishes. Show **all final PNGs inline with absolute paths** for mobile review.

## Measurement and overlap

`production_tools.py mark --episode-dir EP --stage research --event start|end` appends actual timestamps. Use stages research, drafting, content_review, generation, visual_review and handoff. Separate workflow implementation time and user waiting from episode production. Missing token data stays null; retrieve only the relevant run metadata when available, deduplicated by response ID.

Prepare fonts, reference inventory and output paths while independent writing/review runs; wait for required acceptance before provider calls. Avoid a second coordinator or routine additional critics. Batch independent local reads and shell processing; do not poll idle agents every few seconds. Use actual completion messages and retain user-facing progress.

After a run, `usage_summary.py --since ISO --until ISO --output PATH LOG...` aggregates only explicitly supplied relevant logs by unique response ID. Retain the measured-through time; do not treat partial totals as complete billing.
