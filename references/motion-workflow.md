# Existing comic → motion graphics

Use only when the user requests a video adaptation or a revision of one. This route replaces new-comic production for that request; it does not automatically append a video to ordinary comic delivery. Keep the source episode, ID, comic files and topic rotation unchanged.

## Source and baseline

Resolve the named episode from the conversation and actual files. For “latest”, inspect completion records and outputs rather than relying on directory modification time. Read the original final pages, script and relevant QA before adaptation. Record source paths and hashes in `motion/<version>/brief.json`; never silently substitute another episode's characters or artwork.

The approved production direction is exemplified by `episodes/EP-021-national-learning-card/motion/story-v3/output/EP-021-story-v4-voice.mp4`: 30 seconds, 1080×1920, 30 fps, scene-led interactions, simple cream background, game-like music and restrained emphasis at meaningful beats. It is an example, not a mandatory topic, plot or asset library. Verify this file exists before using it as a visual reference. The voice was technically checked; human listening acceptance was not established by its QA.

Unless the current request overrides them, start from these production defaults:

- Vertical 9:16, about 30 seconds; adjust length to intelligible dialogue and the chosen story.
- A concrete action or predicament in the first 1–2 seconds, one central question, visible reactions and an ending that follows from the opening.
- Simple cream or transparent compositing background; omit the original decorative room artwork. Add a necessary prop or setting only when it explains the action.
- Energetic electronic/game music, with selective sound cues and short musical pauses to expose an important line or payoff.
- Local Qwen voice design: native Korean male in his twenties, clear and lively but grounded. Do not reuse the superseded `외노자2` foreign-accent reference by default.

Resolve remaining reversible choices autonomously. Reuse decisions already made in the conversation. If the user authorized end-to-end work, do not restart an interview or insert another script-approval stop; external sharing remains a separate action.

## 1. Adapt the story and review it

Before planning, read `motion-direction-baseline.md`: the user-approved story/direction discussion of 2026-10-04 15:50 KST and subsequent reconstruction. Apply that narrative logic to the selected episode, not just the example video's surface styling.

Dispatch `toon_motion_planner` (GPT-6 Astra low, user: astra-light) using `model-routing.md`'s motion mapping. This agent owns scene adaptation, timed dialogue, interactions, camera, sound cues and art direction. After independent script review passes, dispatch `toon_motion_producer` (GPT-6.1 Sol high) to execute the reviewed plan; the coordinator integrates their outputs. Narrow the source to one useful question rather than reading every panel aloud. Preserve qualifications for every retained factual claim; record omitted material as scope, not as a contradictory simplification. Recheck only changed or time-sensitive connected facts against official evidence.

Plan an opening action → misunderstanding or obstacle → practical discovery → character reaction/payoff. Change what the character is doing, holding, looking at or responding to as information changes. Faster playback, perpetual zooms and more effects alone do not solve a static story. Reveal answers promptly; do not withhold a simple answer merely to extend watch time. Retention improvement is a hypothesis until measured.

Use one canonical `timeline.json` with duration, fps and ordered scenes. Each scene records its start/end, source panel/claim, visible action, character/prop continuity, framing/motion, on-screen text, speaker/voice line and audio cues. Derive captions and the production preview from it, or explicitly validate separately required renderer inputs against it. Do not expose punchline text before its intended reveal.

For information, have the independent content reviewer first read the timed visible/voiced script without the intended answer, then check the selected claims and conditions against source evidence. For humor, use the independent humor reviewer on the adaptation. Fix blocking comprehension, factual and continuity findings before art; at most two script correction passes, then report unresolved findings. Existing comic content locks remain intact; save the adaptation review beside the motion timeline. Do not pretend motion JSON passes the comic's panel-schema validators.

## 2. Generate source artwork for the video

The production agent owns this step and the audio/composition/technical checks below. Give it the reviewed timeline, source references, asset brief and an explicit version-directory write boundary. Preserve others' edits. Return material story changes to planning and affected review rather than improvising a different script.

Inspect the actual episode's final pages and available clean art. Use them as image-generation references to create fresh, text-free motion assets: interaction poses, reactions, close-ups and necessary props. Do not simply animate a screenshot of the original page or replace it with unrelated stock/another episode. Reuse already approved motion assets for a revision when the requested change does not affect them.

Preserve character identity, clothing and drawing style from the source. Read the relevant visual rules and use the shared active-reference resolver for current style references; source identity wins if a newer style would change the character. Record the exact attached reference paths and prompts. Use the native image-generation tool and its skill when applicable; request transparent output for cutouts. Verify real alpha, silhouette edges, hands/props and crop boundaries. An opaque checkerboard is not transparency. For sprite sheets, inspect every cropped cell for neighbouring pose leaks.

Build varied acting around the script: grabbing, turning, offering a phone, reaching, hesitation and relief where appropriate. Separate poses plus camera/keyframe motion are motion-comic animation; do not describe them as continuous character acting or lip sync unless those were actually produced.

## 3. Voice, music and sound

Check the current local arm64 runtime and model capability before use. The reference implementation uses local `mlx-audio` Qwen3-TTS VoiceDesign; a speech server supporting base voice cloning does not necessarily forward VoiceDesign's `instruct` field. Inspect current support instead of assuming an endpoint works. Avoid new downloads or services when an existing local runtime is sufficient.

Keep one voice direction per speaker and test consistency across clips. A repeated seed is not proof of speaker consistency. Prefer natural brisk delivery; fit line lengths before speeding audio. Trim silence without cutting consonants or breaths. Keep visible Korean spelling natural even if pronunciation needs a separate synthesis spelling. Reference cloning requires an explicit suitable reference; the default is voice design without external reference audio.

Keep narration, music and effects as separate stems. Duck music under speech and reserve sound cues for actions, reveals and transitions. For this preset, roughly 140–155 BPM is a starting point, not a fixed requirement. Use local generated or licensed audio with recorded provenance. Avoid clipping; approximately -17 to -14 LUFS with true peak at or below -1 dBTP is a useful starting range, then listen for intelligibility.

Use word timestamps/ASR to find omitted words, cut syllables and caption drift, but never claim ASR verifies voice appeal, accent, age or mix quality. Record listening inspection separately and disclose when it was unavailable.

## 4. Compose and verify

Reuse a suitable local renderer; load the Remotion skill when using Remotion. Keep timing deterministic and source-driven. Browser work follows the user's Aside policy; do not silently switch to Chrome. If a required rendering dependency conflicts with the allowed environment, use an available compatible route or explain the limitation before changing it. For voice-only revisions, preserve the picture and use FFmpeg to replace/mix audio without regenerating artwork or rendering unchanged video.

Deliver H.264/AAC MP4 with `yuv420p` and fast-start metadata for broad mobile playback. Check resolution, duration, fps, full-file decode, caption timing, audio duration and clipping. Inspect hook, transitions, dense text, interactions and ending at mobile scale. The independent visual reviewer checks ordered rendered frames against the source identity and approved timeline; inspect playback when available for timing and movement. Sampled frames alone do not establish full playback quality.

Separate factual review, image review, technical checks and listening/playback findings in `qa/final-report.json`, including what was not checked. Fix affected defects and rerun affected checks only. If unresolved after two targeted repair attempts for the same defect, report it and avoid claiming a complete pass. Do not broaden a voice-only change into a full art rewrite.

## 5. Outputs and delivery

Keep versioned outputs under the same episode's `motion/<version>/`:

- `brief.json`, `timeline.json`: source provenance, scoped story, user decisions and timing.
- `prompts/`, `assets/` (or existing `public/assets/`): actual image inputs, new artwork and audio provenance.
- `src/`, `scripts/` where needed: reproducible composition and audio processing; reuse existing implementations instead of copying environments/model weights.
- `qa/`: adaptation review, visual findings and technical/audio evidence, including agent routing metadata.
- `output/<episode>-<version>.mp4`: delivered video; a short README identifies it and remaining limits.

Preserve previous outputs unless the user explicitly requests their deletion. Show the final file and concise changes. A local absolute path works on the Mac, not as a phone-accessible URL. If mobile access is requested, prepare a responsive player/download page and obtain any missing explicit upload scope before external transfer. Reuse an approved hosting target only within the current authorization. Report access/login restrictions and deployment checks separately from actual phone playback; do not claim a phone test that was not performed.
