# Dialogue Naturalness Review

Run this gate after StoryCriticAgent passes and before ArtDirectorAgent starts. It is a conservative Korean dialogue review, not a rewrite.

## Inputs

Read the current brief and `script.json`, `references/story-rules.md`, `memory/dialogue-style.md`, and the speaking-character entries in `memory/character-bible.json`.

## Check

- Literal or translated phrasing that does not sound spoken in Korean.
- Needlessly formal, nominalized, passive, hedged, or over-connected wording.
- Lines that explain action, setting, or emotion already carried by the image.
- A line that breaks the defined character voice.
- Profanity, configured prohibited tokens, common obfuscations (including initial-only disguises), slurs, sexualized insults, dehumanizing labels, identity-based attacks, or humiliating nicknames in `script.json` or `caption.txt`.

## Preserve

- Story facts, beat order, comic mechanism, opening hook, and sixth-panel payoff.
- Speaker, bubble count, and existing bubble safe-area geometry.
- Named entities, numbers, time expressions, quotations, intentional fragments, repetitions, pauses, laughter, and register.
- The existing visual brief: this review never requests Korean lettering inside generated art.
- Blunt, clipped, self-directed, or mildly sarcastic non-profane Korean that fits the character; do not sanitize allowed roughness into formal Korean.

Do not add facts, jokes, bubbles, prompts, line breaks, or explanatory narration. A changed line must keep the same speaker and communicative job. If a safe improvement would materially change pacing, humour, or the twist, do not apply it automatically; set `requires_story_recheck` to `true`.

## Return contract

Return JSON only:

```json
{
  "pass": true,
  "revision": 0,
  "findings": [
    {
      "panel": 2,
      "bubble": 1,
      "category": "translated_phrase",
      "severity": "minor",
      "original": "...",
      "suggested": "...",
      "reason": "..."
    }
  ],
  "protected_elements": ["opening hook", "sixth-panel timing"],
  "episode_change_rate": 0.0,
  "requires_story_recheck": false
}
```

`category` is one of `translated_phrase`, `stiffness`, `overexplaining`, `voice`, or `language_policy`. `severity` is `minor` or `blocking`. Any profanity, obfuscation, slur, sexualized insult, dehumanizing label, identity-based attack, or humiliating nickname is `blocking`; set `pass` to `false` until the coordinator resolves it. `episode_change_rate` is the proportion of all dialogue characters changed, recorded as a guardrail rather than a target.

The coordinator may apply at most one automatic revision pass. Record all findings, protected elements, change rate, and applied before/after text in `qa-report.md` under `## Agent QA`. If a story recheck is requested, StoryCriticAgent must pass again before image generation. Apply the same preservation rules to `caption.txt` after visual QA; a caption-only edit never triggers image regeneration.
