# Story Rules

## Content-type boundary

For brief 1.2 information, use `informational-workflow.md`: one sourced question-answer card and direction, information-changing inner panels, ending answer/action, one integrated independent content review. Humor engines, three directions, hidden ending, payoff reversal and separate dialogue gate below apply only to humor. Shared dialogue geometry, language, originality and safety still apply; helpful explanations are allowed in information. Caption is supplementary, never the only place holding a core answer or material condition.

## Layout-driven story structure (humor)

1. **Opening hook:** Stop the scroll with an immediately legible visual situation, one concise line, or both. Create curiosity or instant recognition without explaining the setup or spoiling the ending.
2. **Development beats:** Use one state-changing beat for each inner panel. Establish, escalate, complicate, or turn the expectation as the selected panel count needs.
3. **Ending payoff:** Resolve or reverse the expectation with one short, clear, visually playable beat.

Make each panel necessary. The premise must be understandable without the caption. Keep the ending payoff shorter than the development that earns it and do not explain the joke after it lands.

## Direction contract and humor engines

IdeaAgent returns exactly three directions. Each direction records `premise`, `human_truth`, `behavioral_contradiction`, `humor_engine_id`, `engine_explanation`, `hook_promise`, one or more distinct visible `development_changes`, `payoff_reversal`, `beat_signature`, and `why_relatable`. Across the three, use at least two distinct primary engines. WriterAgent realizes one change per selected inner panel and may not silently replace its engine, contradiction, or payoff.

Primary engines: `semantic_authority_reversal`, `personified_cognition_action_contradiction`, `self_rationalization_loop`, `magnitude_mismatch`, `repetition_escalation`, `collective_optimism_reality_collapse`, `moving_goalpost_paralysis`, `social_timing_or_role_reversal`, or `other` with an equally explicit mechanism explanation. Preferred engines break genuine ties only; they are never quotas.

Each development change must visibly alter state or expectation. A panel that only renames, summarizes, or repeats the preceding panel fails. The payoff must reframe the opening, not merely label or restate the visible outcome.

## Opening hook

Panel 1 has one job: make the reader want panel 2. Use at least one of these devices:

- show the surprising consequence before its cause;
- stage a familiar situation at an unusual or exaggerated visual moment;
- use a short confession, contradiction, urgent line, or pointed question;
- begin mid-action with a strong expression, crop, scale contrast, or camera angle.

The hook must remain truthful to the episode. Reject generic greetings, background exposition, vague clickbait, crowded establishing shots, and any line that reveals the ending. Prefer zero or one bubble in the opening; never exceed the two-bubble episode limit. StoryCriticAgent must name the hook mode as `visual`, `dialogue`, or `both`, state the question or expectation it creates, and fail the story when the first panel does not create a clear reason to continue.

## Dialogue

- Use at most two bubbles per panel.
- Give each bubble one communicative job.
- Prefer conversational Korean, concrete verbs, and short clauses.
- Preserve each character's speech habits from `memory/character-bible.json` and `memory/dialogue-style.md`.
- Do not place narration in the image-generation prompt. Store every displayed string only in `script.json`; the deterministic composer inserts it later.
- Avoid emoji, decorative Unicode, sound-effect lettering, hashtags, and forced line breaks in dialogue. The composer owns wrapping.

## Dialogue naturalness gate

After StoryCriticAgent passes and before art direction, run the conservative review in `references/dialogue-naturalness.md`. It may polish only a line's wording when the speaker and communicative job remain unchanged. It must not change story facts, the joke or twist, panel order, bubble count, safe-area geometry, named entities, numbers, intentional fragments, pauses, laughter, or character register. If a change would alter timing or comic meaning, flag it for story recheck instead of applying it.

## Writer panel contract

Each panel must include:

```json
{
  "panel": 1,
  "section": "opening",
  "beat": "opening_hook",
  "scene": "where and when the beat happens",
  "expression": "visible facial expression",
  "action": "one drawable action",
  "props": ["stateful prop"],
  "background": "continuity-relevant background",
  "camera": "shot size and angle",
  "dialogue": [
    {
      "speaker": "character-id",
      "text": "대사",
      "x": 70,
      "y": 65,
      "width": 940,
      "height": 260
    }
  ]
}
```

Use `opening` and `opening_hook` once, `development` once per inner panel, and `ending` with `ending_payoff` once. Dialogue geometry is a required 1080x1350 safe-area request in pixels, not a hand-drawn bubble; the composer deterministically wraps, sizes, and fits the final bubble within it. State every prop whose position or condition matters in later panels.

## Originality and safety

Compare the premise, engine, beat signature, and payoff with `memory/episode-history.json`; matching a broad topic is acceptable, and an engine match alone is not a hard duplicate. A materially matching beat signature or payoff is a hard duplicate failure and must be reframed before drafting. For `instagram_link` episodes, also apply `references/instagram-link-analysis.md`: reuse of the source's abstract ending reversal is allowed, but copied source dialogue, identifiable creator details, logos, copyrighted characters, and original ordered scenes are not.

Apply `memory/banned-topics.json`. Reject hard-banned directions. For review-required topics, remove diagnostic, accusatory, humiliating, exploitative, or identity-based framing and surface any remaining ambiguity to the user. Never imitate a living artist or reproduce a copyrighted character; describe visual qualities rather than artist names.

Dialogue may be blunt, clipped, self-directed, or mildly sarcastic when aimed at the situation. Allow natural non-profane Korean such as `망했다`, `큰일 났네`, `끝났네`, and `이게 맞아?`. Prohibit profanity, disguised or initial-only profanity, slurs, sexualized insults, dehumanizing labels, identity/appearance-based attacks, and humiliating nicknames. Apply this policy to both `script.json` and `caption.txt`; do not sanitize permitted roughness into formal Korean.

## Caption

Write `caption.txt` after the panels pass story QA. Keep it complementary rather than explanatory: one relatable observation, optionally one gentle question, and no claims that the episode has been published.

## Story-quality 1.1 contract

Automatic topic selection must pass source relevance, human observation, behavioral contradiction, a named humor engine, a hook/payoff seed, safety, and duplicate gates before scoring; high scores never override ineligibility. A direct user topic skips the scout. Produce exactly three directions across at least two humor engines, then apply StoryCritic in premise and script stages with at most two total rewrites. Every direction records `human_truth`, `behavioral_contradiction`, `humor_engine_id`, `engine_explanation`, `hook_promise`, one or more `development_changes`, `payoff_reversal`, and `beat_signature`; matching either a prior beat signature or payoff is a hard duplicate. Prohibit profanity and obfuscation, while allowing natural rough non-profane Korean.
