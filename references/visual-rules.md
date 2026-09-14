# Visual Rules

## Canvas and layout

Export every final PNG at exactly 1080x1350 pixels in RGB or RGBA mode.

- `final/page-NN.png`: one sequential final image per selected `output_layout` group. One panel copies its composed source; two stack vertically; three place one panel above two; four use a 2×2 grid.
- `composed/panel-N.png`: internal dialogue-composited panel inputs; never present them as postable exports.
- Keep critical faces, hands, props, and bubble space inside the 54-pixel outer safe margin.
- Reserve uncluttered bubble space identified by the storyboard; do not paint important details behind it.
- Judge legibility at mobile-feed size, not only at full resolution.

## Reference inputs

Resolve the `assets/references/styles` directory marker in both memory JSON files by running `uv run scripts/active_reference.py` just before prompt creation. It returns every non-hidden supported image directly in `styles/`, in filename order, or every supported image in `current/` if `styles/` is empty. For every panel, attach resolved character paths first, then all resolved primary style paths, deduplicating shared images, then explicitly allowed secondary references. Use secondary references only when the user explicitly asks for them. Never attach the directory marker or a removed image from a prior prompt. Paths are project-relative and should normally live under:

```text
assets/references/characters/
assets/references/styles/
assets/references/current/
```

Use all primary images for their shared character grammar and configured palette, sparse composition, mood, and flat textured illustration qualities. Never copy their scenes, furniture, props, poses, text, watermarks, signatures, logos, or handles. Immutable character identity wins over style: never change face, hair, beard, skin tone, body proportions, or expression grammar. Style may not supply a new character design. If an episode has no character, it may use only the style references. For new shared images, only add them to the folder; separate character-only references still require memory registration. Describe observable attributes; never claim to have trained or fine-tuned a model.

## Wardrobe and footwear

Use the character bible's default outfit and footwear unless a panel's `wardrobe_overrides` supplies an explicit `story_reason`. An approved override changes only outfit and footwear; it never changes immutable identity. Carry that override into later panels until another explicit, story-reasoned override replaces it.

## Art direction

- Lock the layout-driven storyboard before generating final raw art.
- Make panel 1 instantly legible at mobile-feed size through one dominant focal subject, a strong expression or action, and a purposeful close, unusual, or consequence-first composition. Preserve empty space for hook dialogue when used.
- Generate every ordered story panel sequentially by default.
- Repeat immutable identity descriptors in every panel prompt: face shape, hair, signature outfit colors, and persistent accessories.
- Repeat continuity state: time, lighting, background, character side, gaze, pose transitions, and prop position or condition.
- Treat the configured palette as strict: use only its allowed colors and restrained tints unless the user explicitly asks otherwise.
- Use one flat or nearly empty color-field background and no more than two story-essential props per panel.
- Balance brisk, playful physical comedy with a quiet, slightly lonely undertone.
- Keep the style and palette consistent with `memory/visual-style.json`; its primary-reference policy takes precedence over character-reference visual treatment.
- Generate only illustration. Exclude letters, Hangul, numbers, captions, speech bubbles, interface text, watermarks, signatures, and logos.

## Prompt file contract

Write one `prompts/panel-N.json` per panel with exactly the stable provider fields `panel`, `revision`, `mode`, `size`, `prompt`, `negative_prompt`, `reference_images`, and `bubble_safe_areas`. Put resolved character references first, then all resolved primary style references, with each shared path attached only once. Encode the strict palette, sparse-background limit, playful/quiet mood, storyboard, identity descriptors, and continuity state in `prompt`. The provider may add run metadata elsewhere but must not change this stable input contract.

## Targeted regeneration

When VisualCriticAgent flags a panel, preserve every passing panel. Revise only the named `prompts/panel-N.json`, increment its revision, and regenerate only `raw/panel-N.png`. For a primary-reference style failure, allow exactly one automatic regeneration; if it still fails, report it for user review. Recompose the matching `composed/panel-N.png` and only the `page-NN.png` group that contains it. Recheck the neighbor panels solely for continuity; do not regenerate them unless they independently fail. Apply the active style policy to a prior episode only when the user requests that episode's regeneration; never batch-regenerate history.

## Visual rejection conditions

Reject and revise a panel for identity drift, malformed or extra hands, fused or floating props, missing scripted actions, unexplained continuity jumps, occupied bubble-safe space, illegible composition at mobile size, palette/style drift, or any generated text-like marks. A primary-reference style failure includes a dominant color outside the approved palette, more than two nonessential props, a busy background, or a mood that misses the playful-but-quiet target. Crop or color differences alone are not grounds for regeneration when they are intentional and continuous.
