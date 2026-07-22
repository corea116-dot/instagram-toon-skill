# Instagram Link Analysis

Run `InstagramPostAnalystAgent` only when the current user message has both an explicit `$instagram-toon` invocation and exactly one direct Instagram post or reel URL. The coordinator must use the explicit invocation metadata when it is available; a natural-language or implicitly selected skill request never activates this route.

Supported canonical forms are `https://www.instagram.com/p/<shortcode>/` and `https://www.instagram.com/reel/<shortcode>/`. Strip query and fragment parameters before analysis. Reject profile, story, live, explore, hashtag, comment, non-Instagram, and multi-link requests by asking for one direct post or reel link. A no-link explicit invocation remains the ordinary EditorialScoutAgent route, and an explicit user topic without a link remains the ordinary `user` route.

## Access boundary

Read only the single linked public post through the current Codex surface. Never log in, use session cookies, bypass a restriction, crawl the creator account, read comments, download source media, or retrieve direct messages. Inspect visible media and only enough visible caption context to form an abstract observation; do not retain original wording.

When a post is private, login-gated, deleted, region- or age-restricted, or insufficiently visible, return `requires_user_input` and stop before IdeaAgent. Do not fall back to unrelated trend research. Ask the user to attach their permitted screenshot or video, or to provide a short summary. That attachment may resume the same already-explicit link route.

## Analyst contract

Give the agent the canonical URL, public media observation, optional user lens (audience, tone, or angle), `memory/banned-topics.json`, and `memory/episode-history.json`. It must return the structured `instagram-source.json` contract only, not a finished script or dialogue.

The analysis extracts only:

- a concise human observation and behavioral contradiction;
- reusable abstract humor, hook, and payoff patterns;
- possible humor engines;
- excluded source elements;
- a duplicate check against episode history;
- a safety check;
- a source-distance check.

Never persist source images, videos, captions, comments, audio lyrics, creator identity or handle, brand claims, logos, exact panel order, or quoted dialogue. The canonical public URL and a short abstract observation are sufficient provenance.

## Re-creation boundary

IdeaAgent turns the abstract analysis into three new directions, and WriterAgent writes the six beats. The original ending reversal or abstract punchline mechanism is allowed to remain. The new story must still change at least three of these five dimensions: setting, protagonist goal, escalation path, props or visual metaphor, and dialogue. Exact source wording, identifiable creator details, logos, copyrighted characters, and the original ordered scenes are prohibited.

StoryCriticAgent runs the source-distance gate before WriterAgent and again after the script. A failed distance, duplicate, or safety check returns to IdeaAgent; it never triggers art generation. Record the source URL, access result, derived topic, safe analysis, changed dimensions, ending-reversal reuse flag, duplicate result, and safety result under `## Agent QA`.
