# Output Contracts

All JSON files use UTF-8, two-space indentation, and a trailing newline. New story-choice, script, and composition artifacts use `"schema_version": "1.1"`; historical 1.0 artifacts remain readable. Paths stored in JSON are relative to the skill root. PNG files are 1080x1350 pixels.

## Contents

- [Episode tree](#episode-tree)
- [`brief.json`](#briefjson)
- [`module-routing.json`](#module-routingjson)
- [`topic-research.json`](#topic-researchjson)
- [`instagram-source.json`](#instagram-sourcejson)
- [`script.json`](#scriptjson)
- [`prompts/panel-N.json`](#promptspanel-njson)
- [`final/composition.json`](#finalcompositionjson)
- [`memory/episode-history.json`](#memoryepisode-historyjson)
- [`qa-report.md`](#qa-reportmd)
- [CLI behavior](#cli-behavior)

## Episode tree

```text
episodes/EP-NNN-kebab-slug/
├── brief.json
├── module-routing.json          # required for new auto-with-overrides episodes
├── topic-research.json          # required only for EditorialScoutAgent selections
├── instagram-source.json        # required only for explicit Instagram-link selections
├── script.json
├── prompts/
│   └── panel-N.json                # one file per ordered story panel
├── raw/
│   └── panel-N.png
├── composed/
│   └── panel-N.png
├── final/
│   ├── page-01.png
│   ├── page-02.png
│   └── page-NN.png
│   └── composition.json
├── caption.txt
└── qa-report.md
```

Use the next zero-padded history number and a short filesystem-safe slug. Never overwrite a different episode to reuse a number.

For every new episode, `final/` contains one postable 1080x1350 `page-NN.png` per `output_layout` group. A group of one copies its composed panel; groups of two, three, and four use the documented layouts. `composed/` retains dialogue-composited panels only as deterministic inputs for targeted regeneration; it is not a publishing export. Schema 1.0 four- and six-panel episodes retain their historical names and exports.

## `brief.json`

Required keys:

```json
{
  "schema_version": "1.1",
  "episode_id": "EP-001",
  "title": "새벽 세 시의 결심",
  "output_layout": [1, 1, 1, 1, 1],
  "topic": "일찍 자려다 휴대폰을 보는 사람",
  "topic_origin": "user",
  "audience": "일상 공감 독자",
  "tone": "가벼운 공감 유머",
  "characters": ["bgoon"],
  "story_module_policy": "auto_with_overrides",
  "directions": [
    {
      "id": "A",
      "premise": "짧은 전제",
      "human_truth": "구체적인 인간적 사실",
      "behavioral_contradiction": "아는 것과 행동의 불일치",
      "humor_engine_id": "self_rationalization_loop",
      "engine_explanation": "작은 허용이 자기 결과를 키운다",
      "hook_promise": "1패널이 남기는 구체적 질문",
      "development_changes": ["상태 변화 1", "상태 변화 2", "상태 변화 3", "상태 변화 4"],
      "payoff_reversal": "오프닝을 다시 읽게 하는 짧은 반전",
      "beat_signature": "engine|escalation|payoff-form",
      "why_relatable": "독자가 공감할 구체적 이유"
    },
    {"id": "B", "premise": "...", "escalation": "...", "twist": "...", "why_relatable": "..."},
    {"id": "C", "premise": "...", "escalation": "...", "twist": "...", "why_relatable": "..."}
  ],
  "selected_direction": "A",
  "duplicate_check": {"matched_episode_ids": [], "result": "pass"},
  "sensitivity_check": {"issues": [], "result": "pass"},
  "status": "draft"
}
```

`topic_origin` is `user` when the user supplied the topic, `editorial_scout` only when EditorialScoutAgent selected it, and `instagram_link` only after the explicit one-link analysis route passes. Direct user topics bypass EditorialScoutAgent. `story_module_policy` is `auto_with_overrides` for new episodes using conditional story modules; historical briefs may omit it and remain readable. `directions` contains exactly three candidates, at least two primary humor engines, and one or more distinct visible development changes per direction. The selected layout determines how many changes WriterAgent realizes. `selected_direction` names one of their IDs. Both check results are restricted to `pass` or `review`; `matched_episode_ids` and `issues` may be empty but the checks may not be omitted from a newly planned episode. `status` is restricted to `draft`, `approved`, or `published`. The deterministic mock composer may also accept a legacy/minimal brief because composition does not make story choices.

## `module-routing.json`

Write this file before IdeaAgent whenever `brief.json.story_module_policy` is `auto_with_overrides`. It is an audit record of selection, not a copy of module output or internal reasoning. Every known module appears exactly once.

```json
{
  "schema_version": "1.0",
  "policy": "auto_with_overrides",
  "mode": "new_episode",
  "overrides": {"enable": [], "disable": []},
  "modules": [
    {"id": "story-architecture", "status": "active", "reason": "new_episode", "runs": 1},
    {"id": "continuity-canon", "status": "skipped", "reason": "no_signal", "runs": 0},
    {"id": "dialogue-persona", "status": "skipped", "reason": "no_signal", "runs": 0},
    {"id": "branch-payoff-lab", "status": "skipped", "reason": "no_signal", "runs": 0},
    {"id": "storyboard-shot-plan", "status": "active", "reason": "new_episode", "runs": 1}
  ],
  "budget": {
    "max_optional_modules": 2,
    "max_branch_rounds": 1,
    "max_script_rewrites": 2,
    "script_rewrites_used": 0
  }
}
```

Module IDs, statuses, modes, counts, nonblank reasons, complete registry, and budgets are validated by `StoryModuleRoutingModel`. Active entries have `runs: 1`; skipped entries have `runs: 0`. Recomposition, validation, and story-unchanged panel regeneration record every module as skipped and load none. The file never stores story text, candidate branches, persona cards, canon extracts, shot plans, or prompt contents.

## `topic-research.json`

Write this file only when `brief.json.topic_origin` is `editorial_scout`. It records why the skill selected a topic during the current invocation; it is not a cache of copied web content. It must contain exactly five candidates using at least three primary humor engines. A candidate may be selected only when it is eligible and has the highest `engagement_priority` among eligible candidates, then the highest score when priorities tie.

```json
{
  "schema_version": "1.1",
  "source_mode": "public_web",
  "search_window_days": 30,
  "sources": [
    {
      "id": "source-1",
      "kind": "public_page",
      "url": "https://example.com/public-signal-one",
      "title": "짧은 공개 출처 제목",
      "observation": "익명화한 일상 신호",
      "engagement": {"likes": 1200, "comments": 86},
      "accessed_at": "2026-07-20T00:00:00+00:00"
    },
    {
      "id": "source-2",
      "kind": "public_page",
      "url": "https://example.com/public-signal-two",
      "title": "두 번째 공개 출처 제목",
      "observation": "반복해서 보인 일상 신호",
      "engagement": {"reactions": 940, "comments": 62},
      "accessed_at": "2026-07-20T00:00:00+00:00"
    }
  ],
  "candidates": [
    {
      "id": "candidate-1",
      "topic": "알람을 여러 번 미루는 아침",
      "source_signal": "공개 출처가 반복적으로 지지한 외출 전 행동",
      "source_relevance": "두 공개 출처 모두 준비 시간이 줄어드는 같은 행동을 뒷받침한다",
      "human_observation": "준비 시간이 줄어들수록 포기 항목이 늘어나는 아침",
      "behavioral_contradiction": "시간을 아끼려다 결정적인 물건을 놓친다",
      "humor_engine_id": "magnitude_mismatch",
      "engine_explanation": "작은 시간 절약이 큰 실수로 뒤집힌다",
      "hook_seed": "급하게 완벽히 준비한 듯한 인물",
      "payoff_seed": "정작 필요한 물건이 다른 것이다",
      "beat_signature": "magnitude_mismatch|shortcut|wrong-essential-item",
      "eligibility": true,
      "gate_results": {"source_relevance": true, "human_observation": true, "behavioral_contradiction": true, "humor_engine": true, "hook_seed": true, "payoff_seed": true, "safety": true, "duplicate": true},
      "story_seed": "준비를 줄여 완벽해졌다고 믿지만 결정적인 물건을 잘못 챙긴다",
      "source_ids": ["source-1", "source-2"],
      "engagement_priority": 82,
      "scores": {
        "relatability": 25,
        "humor": 25,
        "opening_hook": 16,
        "novelty": 9,
        "production_fit": 9,
        "total": 84
      }
    },
    {
      "id": "candidate-2",
      "topic": "집에 돌아와 침대에 잠깐만 눕는 사람",
      "observation": "잠깐의 휴식이 저녁 전체를 바꾸는 일상",
      "story_seed": "잠깐만 누운 사람이 계획을 포기하는 순서",
      "source_ids": ["source-1", "source-2"],
      "scores": {
        "relatability": 24,
        "humor": 23,
        "opening_hook": 15,
        "novelty": 9,
        "production_fit": 9,
        "total": 80
      }
    },
    {
      "id": "candidate-3",
      "topic": "중요한 약속 전에 커피를 찾는 사람",
      "observation": "정신을 차릴수록 시간이 더 부족한 아침",
      "story_seed": "커피를 챙기려다 더 중요한 것을 잊는다",
      "source_ids": ["source-1", "source-2"],
      "scores": {
        "relatability": 23,
        "humor": 23,
        "opening_hook": 15,
        "novelty": 9,
        "production_fit": 8,
        "total": 78
      }
    },
    {
      "id": "candidate-4",
      "topic": "할 일을 시작하기 전에 책상만 정리하는 일상",
      "observation": "시작을 미루며 준비를 완벽하게 만드는 습관",
      "story_seed": "정리만 끝났는데 하루도 끝난다",
      "source_ids": ["source-1", "source-2"],
      "scores": {
        "relatability": 22,
        "humor": 22,
        "opening_hook": 15,
        "novelty": 9,
        "production_fit": 8,
        "total": 76
      }
    },
    {
      "id": "candidate-5",
      "topic": "식사 메뉴를 고르다 시간이 다 가는 사람",
      "observation": "선택지가 많을수록 아무것도 고르지 못하는 순간",
      "story_seed": "모두가 메뉴를 고르는 동안 주인공만 선택을 미룬다",
      "source_ids": ["source-1", "source-2"],
      "scores": {
        "relatability": 22,
        "humor": 22,
        "opening_hook": 14,
        "novelty": 9,
        "production_fit": 8,
        "total": 75
      }
    }
  ],
  "selected_candidate_id": "candidate-1",
  "selected_topic": "알람을 여러 번 미루는 아침",
  "selection_reason": "공개 호응도 우선순위가 가장 높고, 동률 후보보다 점수와 오프닝 장면이 명확하다.",
  "fallback_reason": null
}
```

Every 1.1 candidate records the complete evidence shape shown for `candidate-1`: `source_signal`, `source_relevance`, `human_observation`, `behavioral_contradiction`, `humor_engine_id`, `engine_explanation`, `hook_seed`, `payoff_seed`, `beat_signature`, `eligibility`, and exactly the eight boolean `gate_results` keys. `eligibility` equals the conjunction of those gates; incomplete, renamed, or extra gate keys are invalid. Every candidate remains in the array even if ineligible. Score ranges are relatability 0–30, humor 0–30, opening hook 0–20, novelty 0–10, and production fit 0–10. Scores are calculated only after hard gates; the selected eligible total must be at least 75, with relatability at least 18, humor at least 18, and opening hook at least 12. A `public_web` selection needs two cited `public_page` sources or one cited `official_trend` source. A `local_fallback` selection has no web sources or candidate source IDs and instead has a nonempty `fallback_reason`. Historical 1.0 research remains readable, but `editorial_scout` validation requires both a 1.1 brief and 1.1 research record.

`engagement_priority` is an integer from 0 to 100. A positive value requires at least one cited source with an `engagement` object containing one or more visibly shown `likes`, `comments`, `reactions`, or `upvotes` counts; a missing count is never estimated. The selected eligible candidate must first have the highest engagement priority, then the highest total score. A `local_fallback` selection uses engagement priority `0` for every candidate.

## `instagram-source.json`

Write this file only when `brief.json.topic_origin` is `instagram_link`. It is a compact provenance and transformation record, not a copy of the source post. Keep only the canonical URL and an abstracted observation; never include source media, caption text, comments, audio lyrics, account identity, logo, or source scene sequence.

```json
{
  "schema_version": "1.0",
  "source_platform": "instagram",
  "canonical_url": "https://www.instagram.com/reel/ABC123/",
  "post_type": "reel",
  "access_status": "public",
  "accessed_at": "2026-07-21T12:00:00+09:00",
  "derived_topic": "중요한 일을 앞두고 정리만 하는 사람",
  "human_observation": "중요한 일을 피할수록 사소한 정리가 늘어난다",
  "behavioral_contradiction": "시작하려고 준비하다 정작 시작을 미룬다",
  "humor_engine_candidates": ["self_rationalization_loop"],
  "hook_pattern": "중요한 일 대신 사소한 일에 몰두한 손",
  "payoff_pattern": "준비는 완벽하지만 목표는 그대로인 결말",
  "excluded_elements": ["원문 대사", "창작자 신원", "브랜드와 로고"],
  "source_distance_check": {
    "result": "pass",
    "changed_dimensions": ["setting", "protagonist_goal", "escalation_path"],
    "ending_reversal_reused": true
  },
  "duplicate_check": {"matched_episode_ids": [], "result": "pass"},
  "safety_check": {"issues": [], "result": "pass"},
  "outcome": "pass"
}
```

The canonical URL must be one direct `/p/` or `/reel/` URL. Only a public, completed analysis may enter episode generation. The story may reuse the abstract ending reversal, but must change at least three of setting, protagonist goal, escalation path, props/visual metaphor, and dialogue. `derived_topic` must exactly equal `brief.json.topic`.

## `script.json`

Required keys for a new script are `schema_version`, `episode_id`, `title`, `output_layout`, and ordered `panels`. `output_layout` is a nonempty list of page sizes from 1 through 4; its sum is the story-panel count. The sections are one `opening`, one or more `development`, and one `ending`; beats are `opening_hook`, repeated `development`, and `ending_payoff`. Each panel follows `references/story-rules.md`; each dialogue entry requires `speaker`, `text`, and integer `x`, `y`, `width`, and `height`. This geometry defines the requested safe area on a 1080x1350 panel. The composer, rather than an agent or image model, chooses line breaks and font size and fits the final bubble inside that area. The deterministic tools also accept the 1.0 four- and six-panel contracts as legacy episodes.

```json
{
  "schema_version": "1.1",
  "episode_id": "EP-001",
  "title": "새벽 세 시의 결심",
  "output_layout": [1, 1, 1, 1, 1],
  "panels": [
    {
      "panel": 1,
      "section": "opening",
      "beat": "opening_hook",
      "scene": "침실, 휴대폰 화면 빛만 남은 새벽",
      "expression": "믿기지 않는 표정",
      "action": "이불 속에서 눈을 크게 뜨고 시간을 확인한다",
      "props": ["휴대폰", "베개"],
      "background": "어두운 침실",
      "camera": "휴대폰과 얼굴을 크게 잡은 과감한 근접 구도",
      "dialogue": [
        {
          "speaker": "bgoon",
          "text": "잠깐만, 벌써 3시야?",
          "x": 70,
          "y": 65,
          "width": 940,
          "height": 260
        }
      ]
    }
  ]
}
```

The example shows only panel 1. Every inner panel uses section and beat `development`; the final panel uses `ending` and `ending_payoff`. StoryCriticAgent must record the opening-hook gate described in `references/qa-rubric.md` before art begins.

## `prompts/panel-N.json`

This file is the stable image-provider input.

```json
{
  "schema_version": "1.0",
  "panel": 1,
  "revision": 0,
  "mode": "mock",
  "size": [1080, 1350],
  "prompt": "storyboard, identity, action, camera, and continuity; text-free illustration",
  "negative_prompt": "letters, Hangul, captions, speech bubbles, watermark",
  "reference_images": [
    "assets/references/styles/reference-a.png",
    "assets/references/styles/reference-b.png"
  ],
  "bubble_safe_areas": [{"x": 70, "y": 65, "width": 940, "height": 260}],
  "continuity": {
    "previous_panel": null,
    "locked_characters": [],
    "locked_props": []
  }
}
```

The two paths above are illustrative. Run `uv run scripts/active_reference.py` immediately before prompt creation and use every real path in its `reference_images` array, never the `assets/references/styles` directory marker itself. Every supported image directly in `styles/` is included in filename order; if that folder is empty, every supported image directly in `current/` is the fallback. For this skill, `reference_images` begins with resolved authoritative character references, followed by all resolved primary style references, deduplicating shared images, then explicitly allowed secondary references. This order applies to every new panel and user-requested targeted regeneration. `prompt` must lock immutable character identity and specify the effective wardrobe and footwear state. A panel may add `wardrobe_overrides` in `script.json` only with `character_id`, `outfit`, `footwear`, and `story_reason`; the state persists until another override. The current Codex image feature, deterministic mock generator, and future `scripts/generate_panel.py` must all output an exact 1080x1350 `raw/panel-N.png` from this contract.

## `final/composition.json`

Record deterministic layout decisions:

```json
{
  "schema_version": "1.1",
  "canvas": [1080, 1350],
  "output_layout": [1, 1, 1, 1, 1],
  "layouts": [
    {
      "panel": 1,
      "bubble": 1,
      "box": {"x": 273, "y": 122, "width": 533, "height": 146},
      "safe_area": {"x": 70, "y": 65, "width": 940, "height": 260},
      "font_size": 56,
      "lines": ["오늘은 진짜 일찍 잔다"]
    }
  ]
}
```

## `memory/episode-history.json`

The updater is idempotent by `episode_id`. New 1.1 entries also contain `humor_engine_id`, `beat_signature`, and `hook_mode`; 1.0 entries may omit them and remain readable. Re-running an update replaces the matching entry instead of appending a duplicate.

```json
{
  "schema_version": "1.0",
  "episodes": [
    {
      "episode_id": "EP-001",
      "title": "새벽 세 시의 결심",
      "topic": "일찍 자려다 휴대폰을 보는 사람",
      "premise": "일찍 자겠다는 결심과 한 번만 더 보겠다는 유혹",
      "twist": "잠은 내일의 나에게 미룬다",
      "humor_engine_id": "self_rationalization_loop",
      "beat_signature": "self_rationalization_loop|permission-escalation|defer-tomorrow",
      "hook_mode": "both",
      "characters": ["bgoon"],
      "status": "draft",
      "path": "episodes/EP-001-example",
      "created_at": "2026-07-19T00:00:00+00:00"
    }
  ]
}
```

## `qa-report.md`

Include episode path, validation timestamp, premise-stage verdict, script score and revision count, every hard-gate result, failure class and reroute, dialogue-naturalness and language-policy result, continuity result, panel-addressed visual findings, required file result, dimensions, bubble-boundary result, and an overall `PASS` or `FAIL`. When `module-routing.json` exists, include a `Story modules` section with policy, mode, active/skipped IDs and reasons, run counts, and budget usage without copying module outputs. For an EditorialScoutAgent episode, under `## Agent QA` also record source mode, selected candidate ID, eligibility/gate results, total score, selection reason, duplicate and sensitivity findings, and fallback state. Record the dialogue-naturalness pass state, revision number, protected elements, change rate, story-recheck state, and each applied panel/bubble change with its original text and reason. `validate_episode.py` may replace its deterministic validation section, but must preserve an existing Agent QA section byte-for-byte. Never describe publishing as complete unless a separately approved external action actually occurred.

## CLI behavior

All three scripts are standalone CLIs invoked as `uv run scripts/<name>.py ...`. They print one clear result path to stdout on success. Invalid arguments, malformed input, or failed checks produce a concise message naming the affected file on stderr and exit with a nonzero status. Provider credentials are never required for `--mock`.

## Story-quality 1.1 contract

For each direction, record `human_truth`, `behavioral_contradiction`, `humor_engine_id`, `engine_explanation`, `hook_promise`, one or more distinct visible `development_changes`, `payoff_reversal`, and `beat_signature`. WriterAgent realizes one change per selected inner panel. For the selected direction, also record the selected engine, selected beat signature, and selected hook promise. Automatic selection records the source-relevance, human-observation, behavioral-contradiction, named-engine, hook/payoff-seed, safety, and duplicate gate outcomes before scoring; high scores cannot override an ineligible result. A direct user topic records that scout was skipped. Exactly three directions must cover at least two humor engines; StoryCritic records premise and script stages and no more than two total rewrites. Treat matching beat signatures or payoffs as hard duplicates. Do not record profanity or obfuscated profanity in generated story text; rough non-profane Korean is allowed.
