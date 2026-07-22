# Visual Rules

## Canvas and layout

Export every final PNG at exactly 1080x1350 pixels in RGB or RGBA mode.

- `final/opening.png`: one full opening panel using `assets/templates/carousel.svg`.
- `final/development-four-panel.png`: two columns by two rows using `assets/templates/four-panel.svg` and source panels 2–5 in order.
- `final/ending.png`: one full ending panel using `assets/templates/carousel.svg`.
- `composed/panel-1.png` through `composed/panel-6.png`: internal dialogue-composited panel inputs; never present them as postable exports.
- Keep critical faces, hands, props, and bubble space inside the 54-pixel outer safe margin.
- Reserve uncluttered bubble space identified by the storyboard; do not paint important details behind it.
- Judge legibility at mobile-feed size, not only at full resolution.

## Reference inputs

Resolve character references from each character's `reference_images` in `memory/character-bible.json`. Resolve style references from `memory/visual-style.json`. For every panel, attach every path in `reference_policy.primary_reference_images`, in its listed order, before any character or secondary reference. Use secondary references only when the user explicitly asks for them. Paths are project-relative and should normally live under:

```text
assets/references/characters/
assets/references/styles/
```

Use the selected primary images only for their configured palette, sparse composition, mood, and flat textured illustration qualities. Never copy their cat, people, scene, furniture, props, pose, text, watermark, signature, logo, or handle. If a character reference conflicts with the selected style, the selected style wins; retain `bgoon` through role and action rather than through competing visual treatment. If references are absent, use the written bibles without inventing permanent identity traits. When the user supplies references, update the memory paths and describe observable attributes; never claim to have trained or fine-tuned a model.

## Art direction

- Lock the six-beat storyboard before generating final raw art.
- Make panel 1 instantly legible at mobile-feed size through one dominant focal subject, a strong expression or action, and a purposeful close, unusual, or consequence-first composition. Preserve empty space for hook dialogue when used.
- Generate panels 1 through 6 sequentially by default.
- Repeat immutable identity descriptors in every panel prompt: face shape, hair, signature outfit colors, and persistent accessories.
- Repeat continuity state: time, lighting, background, character side, gaze, pose transitions, and prop position or condition.
- Treat the configured palette as strict: use only its allowed colors and restrained tints unless the user explicitly asks otherwise.
- Use one flat or nearly empty color-field background and no more than two story-essential props per panel.
- Balance brisk, playful physical comedy with a quiet, slightly lonely undertone.
- Keep the style and palette consistent with `memory/visual-style.json`; its primary-reference policy takes precedence over character-reference visual treatment.
- Generate only illustration. Exclude letters, Hangul, numbers, captions, speech bubbles, interface text, watermarks, signatures, and logos.

## Prompt file contract

Write one `prompts/panel-N.json` per panel with exactly the stable provider fields `panel`, `revision`, `mode`, `size`, `prompt`, `negative_prompt`, `reference_images`, and `bubble_safe_areas`. Put all `primary_reference_images` first in `reference_images` for every new panel and user-requested targeted regeneration; append character paths only afterward. Encode the strict palette, sparse-background limit, playful/quiet mood, storyboard, identity descriptors, and continuity state in `prompt`. The provider may add run metadata elsewhere but must not change this stable input contract.

## Targeted regeneration

When VisualCriticAgent flags a panel, preserve every passing panel. Revise only the named `prompts/panel-N.json`, increment its revision, and regenerate only `raw/panel-N.png`. For a primary-reference style failure, allow exactly one automatic regeneration; if it still fails, report it for user review. Recompose the matching `composed/panel-N.png` and only its affected final image: opening for panel 1, development composite for panels 2–5, or ending for panel 6. Recheck the neighbor panels solely for continuity; do not regenerate them unless they independently fail. Apply the active style policy to a prior episode only when the user requests that episode's regeneration; never batch-regenerate history.

## Visual rejection conditions

Reject and revise a panel for identity drift, malformed or extra hands, fused or floating props, missing scripted actions, unexplained continuity jumps, occupied bubble-safe space, illegible composition at mobile size, palette/style drift, or any generated text-like marks. A primary-reference style failure includes a dominant color outside the approved palette, more than two nonessential props, a busy background, or a mood that misses the playful-but-quiet target. Crop or color differences alone are not grounds for regeneration when they are intentional and continuous.
