# QA Rubric

## Informational review

Use the twelve evidence-backed checks and two ordered reviewer inputs in `informational-workflow.md`. One independent reviewer replaces the separate premise/script/dialogue/continuity roles below. No required numeric score or humor. Generic money advice that omits the selected product's identity, benefit conditions or risk must fail. Test the unaided reader's answer against the actual topic contract and claims; a recorded PASS is not proof of meaning by itself. Changed meaning or wording invalidates approval until affected content is reviewed again; geometry-only changes require layout/visual checks.

Review speech and information-card text together. The card form must fit its content, with labels, units and material qualifications unambiguous. Bubbles interpret rather than recite the entire card. In final images, every card panel also contains a substantial recognizable character visibly explaining it and a readable speech bubble. Card-only slides, character stickers, obscured faces, and unsupported implications from arrows/grouping fail. Card text counts toward the same text budget and final-page font limit, not a hidden allowance.

Within the same review, check that character-led panels (solo or interacting cast) remain the default, each card has a comprehension reason, and panels without cards do not lose facts or become filler reactions. Apply the scene policy in `visual-rules.md`: compare planned cast, setting, action and interaction with final images; flag missing interactions or repetitive presenter framing, not merely consecutive cards. A purposeful shared room is valid continuity. Mixed presentation has no fixed ratio or forced supporting cast. Do not add a reviewer or another approval gate for this check.

For both routes, inspect final pages in reading order; inspect raw only for suspected defects. Keep visual and cheap deterministic safeguards below. The public-engagement ranking below is historical only; current keyword search uses `keyword-evidence.md`, never likes or a local fabricated fallback.

## EditorialScoutAgent (legacy public-engagement humor)

Run this gate only when `brief.json.topic_origin` is `editorial_scout`. It is not a substitute for StoryCriticAgent. Before any score, require source relevance for the concrete observation, a one-sentence contradiction, an explicit humor engine, visual hookability, payoff pressure, and safety/originality. Record every failed candidate among the exactly five, mark it ineligible, and never select it regardless of score. The five candidates must contain at least three distinct primary humor engines.

Reject a candidate before scoring when it is unsafe, a review-required topic that cannot be safely reframed, a duplicate premise or comic mechanism, unsupported by its required public-web sources, based on a real person's or brand's claim, or copied from a post.

Score each of exactly five candidates after hard-gate evaluation: relatability 0–30, humor 0–30, opening hook 0–20, novelty 0–10, and production fit 0–10. Record public engagement only from normally accessible, visibly shown likes, comments, reactions, or upvotes. Choose the highest-engagement-priority eligible candidate, then the highest score if priorities tie. It must total at least 75, with relatability at least 18, humor at least 18, and opening hook at least 12. A public-web selection needs two cited public pages or one cited official trend source. `local_fallback` may contain no web sources or engagement priority and must state why the web search could not produce a safe candidate.

The selected topic must match `brief.json.topic`, and the full result must pass the `topic-research.json` schema. When no candidate passes, stop before story drafting and ask one concise user question. When one passes, continue automatically into IdeaAgent and StoryCriticAgent.

## InstagramPostAnalystAgent

Run only after the explicit one-link route passes. It may inspect one public direct post or reel and must return a valid `instagram-source.json`. Reject login-gated, private, removed, inaccessible, or insufficiently visible posts with `requires_user_input`; do not replace the user's chosen source with a trend. Before IdeaAgent, require public access, a human observation, behavioral contradiction, at least one named engine, a duplicate pass, a safety pass, and three changed non-ending story dimensions. The source ending reversal may be retained. Before and after WriterAgent, StoryCriticAgent must fail exact source wording, creator identity, logos, copyrighted characters, or copied ordered scenes, and reroute failure to IdeaAgent.

## StoryCriticAgent premise mode

Run after IdeaAgent and before WriterAgent. Review all exactly three directions against these hard gates: human contradiction, explicit engine, specific hook promise, one or more distinct visible development changes, payoff reversal, duplicate, and safety. Confirm that WriterAgent can assign one change to every selected inner panel. Return passing direction IDs and classify each failure as `topic`, `mechanism`, `hook`, `beats`, `payoff`, `duplicate`, or `safety`; state `reroute_to` as `another_direction`, `idea_agent`, `next_editorial_candidate`, or `stop_for_user_input`. Numeric scores do not apply in premise mode.

```json
{
  "stage": "premise",
  "passing_direction_ids": ["A"],
  "findings": [{"direction_id": "B", "pass": false, "failed_gates": ["beats"], "failure_class": "beats", "reroute_to": "idea_agent", "reason": "..."}]
}
```

## StoryCriticAgent script mode

Score each dimension from 0 to 20; the total is out of 100.

| Dimension | 17-20 | 9-16 | 0-8 |
| --- | --- | --- | --- |
| Comprehension | Premise and beat order are immediate | One inference is unclear | Sequence or subject is confusing |
| Relatability | Specific, recognizable observation | Broad but plausible | Remote, contrived, or alienating |
| Dialogue brevity | Every line earns its space | Minor trimming is possible | Dense, repetitive, or explanatory |
| Twist effect | Short, fair, and surprising | Understandable but expected | Missing, confusing, or overexplained |
| Originality | Distinct premise and comic mechanism | Familiar with a fresh detail | Duplicates history or a stock punch line |

Evaluate the opening hook separately from the 100-point score. It passes only when panel 1 is instantly legible, creates a specific question or expectation that panel 2 can develop, and earns attention through a visual device, concise dialogue, or both. It fails for generic setup, exposition, vague clickbait, a crowded focal hierarchy, or an early ending reveal. Return `hook_question`.

All script hard gates must pass independently of the score: `human_contradiction_visible`, `engine_matches_direction`, `hook_creates_specific_question`, `all_development_panels_change_state`, `no_label_only_or_explanatory_dialogue`, `payoff_reframes_opening`, `no_visible_outcome_restatement`, `mechanism_and_payoff_not_duplicate`, and `language_policy_pass`. The payoff result includes `payoff_reframes` and a one-sentence explanation. A score of 80 or more cannot override any hard-gate failure.

Return:

```json
{
  "opening_hook": {
    "pass": false,
    "mode": "visual",
    "reason": "what makes the reader continue or why the hook fails",
    "hook_question": "specific unresolved question or null",
    "revision_instruction": "panel-1 action when failed, otherwise null"
  },
  "scores": {
    "comprehension": 0,
    "relatability": 0,
    "dialogue_brevity": 0,
    "twist_effect": 0,
    "originality": 0
  },
  "hard_gates": {"human_contradiction_visible": true, "engine_matches_direction": true, "hook_creates_specific_question": true, "all_development_panels_change_state": true, "no_label_only_or_explanatory_dialogue": true, "payoff_reframes_opening": true, "no_visible_outcome_restatement": true, "mechanism_and_payoff_not_duplicate": true, "language_policy_pass": true},
  "payoff_reframes": {"pass": true, "explanation": "..."},
  "total": 0,
  "pass": false,
  "failure_class": "hook",
  "reroute_to": "writer_agent",
  "revision_instructions": ["panel-addressed, actionable change"]
}
```

Pass only when the total is 80 or higher and every hard gate passes. WriterAgent receives exact revision instructions only for script-local `hook`, `payoff`, or `dialogue` failures. Route `topic` to the next eligible EditorialScout candidate (up to three), `mechanism` or `beats` to IdeaAgent (two rounds), `duplicate` to a different direction or topic, and `safety` to one reframe then user input. Permit no more than two total script rewrite rounds. Never regenerate art for a story failure.

## DialogueNaturalnessAgent

Run only after story QA passes and before art direction. This is a conservative Korean dialogue check, not a new drafting round. Check only translated or stiff phrasing, needless nominalization or hedging, dialogue that repeats visible information, character-voice mismatch, configured profanity, common obfuscations, and contextual indirect abuse. Preserve permitted blunt non-profane Korean rather than formalizing it.

Preserve the story facts and comic mechanism, panel beat, speaker, bubble count, dialogue geometry, named entities, numbers, time expressions, quotations, intentional fragments, repetitions, pauses, laughter, and register. Do not add a fact, a new joke, a new bubble, or a line break. A change that would materially alter the opening hook or ending payoff requires story recheck instead of an automatic edit. Allow at most one automatic revision round.

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
  "protected_elements": ["opening hook", "ending timing"],
  "episode_change_rate": 0.0,
  "requires_story_recheck": false
}
```

Use `minor` when a same-job wording polish is safe and `blocking` when the wording cannot be changed without altering the story. `pass` is false for any unresolved blocking finding. `episode_change_rate` is the share of dialogue characters altered across the episode; use it as a warning signal, not a license to rewrite. Record each applied change and its original text in Agent QA.

## ContinuityAgent

Check face, hair, outfit, palette, signature props, voice, background, time, lighting, screen direction, positions, and prop state. Return an empty `issues` array when clean.

```json
{
  "pass": false,
  "issues": [
    {"panel": 3, "field": "props", "problem": "...", "required_change": "..."}
  ]
}
```

## VisualCriticAgent

Inspect these ten dimensions in priority order:

1. Character consistency
2. Hands and prop anatomy
3. Script-to-image match
4. Cross-panel continuity
5. Reserved bubble space
6. Mobile readability
7. Style and palette consistency
8. Strict primary-reference palette adherence
9. Purposeful setting/props, planned cast interaction and clear visual hierarchy
10. Playful action balanced with a quiet, slightly lonely undertone

Return only observed problems; do not request a whole-episode rerender for a panel-local failure.

```json
{
  "pass": false,
  "issues": [
    {
      "panel": 2,
      "dimension": "hands_and_props",
      "severity": "blocking",
      "problem": "...",
      "revision_prompt": "Preserve all approved details; change only ..."
    }
  ]
}
```

Any generated lettering, identity drift, missing scripted action/cast, malformed hand/prop, unsafe bubble placement, wrong output size, or primary-reference style failure is blocking. Identity drift includes changed face, hair, beard, skin tone, body proportions, or expression grammar, including one character inheriting another's traits. A wardrobe or footwear change without a script `story_reason` is blocking continuity. A primary-reference style failure includes a dominant unapproved hue, clutter obscuring the action or text, a copied reference scene, or a missed planned mood. Necessary settings and supporting characters are not failures by themselves. Character identity and wardrobe continuity always outrank style. Regenerate the failing panel once with resolved authoritative character references first and all current primary style references after them, deduplicating shared images; if it still fails, mark `review_required` and stop automatic retries. Report informational polish separately and do not automatically regenerate for it.

## Deterministic validation

`validate_episode.py` must check required files, JSON readability, required schema versions including prompt and composition manifests, `output_layout` sum and per-page maximum of four, section and beat order, bubble count, raw/composed/final PNG readability, exact 1080x1350 dimensions for every raw provider image, internal composed panel, and final image, bubble boxes inside safe areas, and one sequential `page-NN.png` delivery output per selected group. It also validates 1.0 four- and six-panel episodes with their legacy exports. It writes `qa-report.md`, prints that path on success, and exits nonzero with a clear error on failure.

Mock end-to-end QA must also prove:

- repeated identical runs produce identical output;
- single-panel mode leaves other raw, composed, and final-image hashes unchanged;
- long unspaced Korean text wraps into multiple lines;
- bubble boxes remain inside the canvas and their assigned safe areas;
- temporary staging files are removed.

## Story-quality 1.1 contract

Before any topic score, fail candidates that lack source relevance, human observation, behavioral contradiction, a named humor engine, hook/payoff seed, safety clearance, or duplicate clearance; a high score cannot override ineligibility. A direct user topic skips scouting. Evaluate exactly three directions across at least two humor engines in two StoryCritic stages (premise, then script), with no more than two total rewrites. Review and report `human_truth`, `behavioral_contradiction`, `humor_engine_id`, `engine_explanation`, `hook_promise`, one or more `development_changes`, `payoff_reversal`, and `beat_signature`; the selected engine, signature, and hook must be explicit. The same beat signature or payoff is a hard duplicate. Reject profanity and obfuscation, but allow rough non-profane Korean when contextually natural.
