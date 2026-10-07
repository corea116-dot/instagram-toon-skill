# Information card: approved #01 taped memo

The user selected sample **01 테이프 메모지** on 2026-10-07. Use `taped_memo_v1` as the default skin when a new panel needs an information card. This selects the card's visual treatment; content grouping, row count and card presence still follow the story. Preserve the scene-led and same-panel presenter rules.

## Resources and appearance

- `assets/information-cards/taped-memo-v1/preview.png`: the selected design sample, for composition reference only. Its wording is sample content, not facts to reuse. Never attach this lettered preview as a raw-art generation reference.
- `assets/information-cards/taped-memo-v1/style.json`: versioned colors, pen geometry and existing licensed font paths; shared by comics and motion compositions.
- `assets/information-cards/taped-memo-v1/example-card.json`: executable geometry example. Replace its sample wording and presenter with the approved episode's actual content/cast, then run the existing gates.
- `scripts/information_card_styles.py`: deterministic paper, two tape strips, rounded labels and marker strokes. `rendering.py` handles actual text fitting and composition.

Use cream paper #FFFDF7, small warm shadow #DED6C7, loose dark pen #292824 and two muted tape strips #DFD4B7 near the upper corners. Keep the cream color confined to the card; do not tint the whole comic page. Labels use soft yellow #F0D99D or mint #D6E4D9. The corresponding restrained markers are #F7DF9D / #D0E1D1. Use thin #D5CFC2 row dividers when grouping helps; do not put a divider or two rows in every card.

## Script and lettering

Set `information_card.style: "taped_memo_v1"` explicitly for new cards. `format` remains a free description of the information structure, independent of this skin. An absent style retains the previous renderer for historical scripts.

Card texts optionally use:

- `role: "body"` (default): existing Nanum BaReunHiPi handwriting and normal content fitting.
- `role: "label"`: rounded Cafe24 Ssurround letters inside a small outlined tag; `accent: "yellow"` or `"mint"` selects the fill. Use for a short category/condition heading.
- `role: "emphasis"`: Cafe24 Ssurround letters for a short key number or word. Optional `accent` adds a marker behind the actual glyph bounds, before drawing text. Omit the accent for bold only.

These roles/accents require the explicit style; `body` does not accept an accent. Reserve separate nonoverlapping text boxes for an emphasized number and its surrounding wording, in reading order. Keep complete conditions and exceptions together in the same visual group. Do not change source wording or omit qualifiers to fit a tag. All text fragments remain in content review and the combined budget.

Use the paper's inner area: leave at least 24px of native margin at its sides/bottom and about 12% of the card height above text for the tape. Reserve a little breathing room between adjacent inline fragments because each text box has 12px internal padding. Label height around 64–90px and body/emphasis height around 100–120px are starting values for a wide native slot, not mandatory sizes. Resize layout to the actual slot and enforce the existing 34px effective minimum; split/reflow dense content instead of hiding it.

Do not use a full-area shape that repaints the paper, border or tape. Shapes remain available for content-specific cells/dividers. Fit all decoration inside the reserved card area and keep it away from presenter and speech regions. The existing source checks, lock, preflight and final visual review remain required; this style adds no approval stage.

## Motion information overlays

Use this treatment for newly planned explanatory cards/callouts when the motion story needs them. Read the same versioned colors/font paths and recreate the paper/tape/tag/text as editable layers in the active renderer; the Python helper can also draw decoration without using the sample's pixels. Keep glyphs clear throughout entrance/exit, reveal conditions with their numbers and animate the card only at meaningful information beats. This does not turn ordinary speech captions into memo cards or force a card into every scene. Preserve the approved narrative/audio pipeline. Existing comic pages and videos stay unchanged unless their revision is requested.

## Existing visual QA

Check tape stays above text; paper/labels/markers do not cover glyphs or the presenter; body handwriting and round label/number type are distinguishable; marker colors remain restrained; grouping preserves each qualification; all words are readable in the delivered frame. Do not accept JSON declarations alone as visual proof.
