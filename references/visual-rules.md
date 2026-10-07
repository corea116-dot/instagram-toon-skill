# Visual Rules

When a new information card is useful, apply approved #01 `taped_memo_v1` from [information-card-style.md](information-card-style.md): cream paper, loose pen border, two small tape strips, yellow/mint labels and restrained number markers. Keep this skin separate from content structure and raw-art generation.


## Canvas and layout

Export every final PNG at exactly 1080x1350 pixels in RGB or RGBA mode.

- `final/page-NN.png`: one sequential final image per selected `output_layout` group. One panel copies its composed source; two stack vertically; three place one panel above two; four use a 2×2 grid.
- `composed/panel-N.png`: internal dialogue-composited panel inputs; never present them as postable exports.
- Keep critical faces, hands, props, and bubble space inside the 54-pixel outer safe margin.
- Reserve uncluttered bubble space identified by the storyboard; do not paint important details behind it.
- Character-led panels have no information card or reserved card rectangle: show a substantial expressive character carrying a meaningful action, with dialogue space only. Short factual explanations may use this mode too. Follow the planned mixed sequence, vary framing/gestures, and do not turn every panel into a presenter slide. Do not require a fixed card ratio or strict alternation.
- For informational cards, reserve card and presenter areas too. The same panel must show a recognizable, substantial character explaining the card through a speech bubble and a relevant gesture or gaze. No card-only slides or decorative character stickers. Choose table/calendar/comparison/sequence or another arrangement for the content rather than a repeated fixed template; the information workflow owns the full rule.
- Judge legibility at mobile-feed size, not only at full resolution.

## Speech-bubble composition

For information and humor, every deterministically composed speech bubble has one white body-and-tail shape with a continuous outer outline. Use `scripts/rendering.py` (`_draw_speech_bubble`); do not independently outline the rounded body and triangle, which introduces a horizontal seam at their join. This applies to default and speaker-anchored tails in every output layout. Keep the interior of the join white and open while retaining the outer body and tail edges.

During the existing final-page visual review, check body-to-tail joins for internal strokes, gaps and broken outlines. An internal horizontal join line is a composition defect: correct the common compositor and recompose the affected pages from their existing raw art. Recheck the changed bubbles and readability; unchanged content does not need another content review.

## Reference inputs

Resolve the `assets/references/styles` directory marker in both memory JSON files by running `uv run scripts/active_reference.py` just before prompt creation. It returns every non-hidden supported image directly in `styles/`, in filename order, or every supported image in `current/` if `styles/` is empty. For every panel, attach resolved character paths first, then all resolved primary style paths, deduplicating shared images, then explicitly allowed secondary references. Use secondary references only when the user explicitly asks for them. Never attach the directory marker or a removed image from a prior prompt. Paths are project-relative and should normally live under:

```text
assets/references/characters/
assets/references/styles/
assets/references/current/
```

Use all primary images for their shared character grammar and configured palette, visual hierarchy, mood, and textured illustration qualities. Adapt general staging principles such as depth, relative scale, gaze direction and interaction to an original scene. Do not reproduce a reference's specific scene, prop arrangement, pose sequence, text, watermark, signature, logo or handle. This originality rule does not prohibit settings or supporting characters. Immutable identity wins over style: never change a registered character's face, hair, beard, skin tone, body proportions or expression grammar. A new supporting character needs its own defined identity; shared style images are not proof of its exact appearance. Describe observable attributes; never claim training or fine-tuning.

## Scene policy

- Character-led means characters carry the scene, not that only the protagonist may appear. Choose solo action, interaction, card explanation or a concrete next action by the panel's job, with no fixed ratio or mandatory supporting cast.
- In `scene`, explicitly name the on-screen cast, place and situation. Record each person's action, relative position and gaze in `action`/`camera`; use `dialogue.speaker` to identify the speaker. The episode character roster and identity locks do not require every character to appear in every panel.
- Use a concise, recognizable setting when it explains the situation. Distinguish spatial cues such as a desk/window from handled story props; neither has a universal numerical cap. Keep only elements that support the action, spatial continuity or understanding. A flat background remains useful for emphasis, but is not the default for every panel.
- Give supporting characters a meaningful task or relationship, distinguish their identity from the protagonist, and preserve it on reappearance. Register only characters the episode needs. Do not borrow a reference guard automatically or turn a fictional peer into an unverified official authority.
- Plan text, cast and setting at the delivered page-cell size. Do not solve crowding by deleting material facts or shrinking people into stickers. A close-up may omit room details once the space is established. Reusing a room is valid continuity when the action changes.
- Review the sequence for repeated presenter staging, not just changes in hand pose. The opening should make its situation/question legible; the ending should show or clearly support the reader's next action. Variety must serve the content, not become a scenery or character quota.

## Wardrobe and footwear

Use the character bible's default outfit and footwear unless a panel's `wardrobe_overrides` supplies an explicit `story_reason`. An approved override changes only outfit and footwear; it never changes immutable identity. Carry that override into later panels until another explicit, story-reasoned override replaces it.

## Art direction

- Lock the layout-driven storyboard before generating final raw art.
- Make panel 1 instantly legible at mobile-feed size through one dominant focal subject, a strong expression or action, and a purposeful close, unusual, or consequence-first composition. Preserve empty space for hook dialogue when used.
- Generate every ordered story panel sequentially by default.
- Repeat immutable identity descriptors in every panel prompt: face shape, hair, signature outfit colors, and persistent accessories.
- Repeat continuity state: time, lighting, background, character side, gaze, pose transitions, and prop position or condition.
- Treat the configured palette as strict: use only its allowed colors and restrained tints unless the user explicitly asks otherwise.
- Apply the scene policy above for setting density and purposeful props; do not force a flat background or a fixed prop count.
- Balance brisk, playful physical comedy with a quiet, slightly lonely undertone.
- Keep the style and palette consistent with `memory/visual-style.json`; its primary-reference policy takes precedence over character-reference visual treatment.
- Generate only illustration. Exclude letters, Hangul, numbers, captions, speech bubbles, interface text, watermarks, signatures, and logos.

## Prompt file contract

Write one `prompts/panel-N.json` per panel using the executable `PromptManifestModel` and `references/output-schema.md`. Put resolved character references first, then all resolved primary style references, with each shared path attached only once. Encode the palette, planned cast and setting, mood, storyboard, identity descriptors, and continuity state in `prompt`. Identity descriptions are conditional on appearance, not a demand to draw the whole roster. For card panels include the model's card/presenter reserved areas and interaction in the prompt, without visible card strings. Raw art must not paint a duplicate card or any text; the deterministic compositor adds the designed card and lettering.

## Targeted regeneration

When VisualCriticAgent flags a panel, preserve every passing panel. Revise only the named `prompts/panel-N.json`, increment its revision, and regenerate only `raw/panel-N.png`. For a primary-reference style failure, allow exactly one automatic regeneration; if it still fails, report it for user review. Recompose the matching `composed/panel-N.png` and only the `page-NN.png` group that contains it. Recheck the neighbor panels solely for continuity; do not regenerate them unless they independently fail. Apply the active style policy to a prior episode only when the user requests that episode's regeneration; never batch-regenerate history.

## Visual rejection conditions

Reject and revise a panel for identity drift, malformed or extra hands, fused or floating props, missing scripted actions or cast, unexplained continuity jumps, occupied bubble-safe space, illegible composition at mobile size, palette/style drift, or any generated text-like marks. A primary-reference style failure includes a dominant color outside the approved palette, incidental clutter that competes with the action/text, a copied reference scene, or a mood that misses the planned tone. A necessary setting or supporting character is not itself a style failure. Crop or color differences alone are not grounds for regeneration when intentional and continuous.

For card panels, also reject a missing explaining character/bubble, card text covering the character, illegible card text, or visual grouping that misstates a condition. For character-led panels, do not demand a card; check the meaningful action and information against the script. Check the whole sequence for unnecessary cards and repetitive layouts. A JSON presenter box alone is not visual evidence. Inspect the final composited page at its delivered size.

## Frame-first art and fill check

For `frame_native_v1`, storyboard each actual output slot before generating art. Compose wide/short slots as wide/short scenes; continue the scene to all four frame edges, including behind planned overlays. Do not reserve a uniform blank upper band or bake in borders/gutters. Keep recognizable faces, hands and essential props crop-safe and outside dialogue/card overlays. Crop raw art proportionally before lettering, then fit text in native pixels.

During the existing ordered final-page visual review, inspect every tile for scene fill, artificial side/top blank bands, distorted proportions, cut faces/hands/props, cropped lettering and mobile readability. Intentional negative space is permitted when the scene calls for it; a numeric occupancy threshold cannot establish visual quality. Record any failure in the existing visual findings and revise only affected panels.
