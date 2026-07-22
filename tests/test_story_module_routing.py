#!/usr/bin/env -S uv run --script
# /// script
# requires-python = ">=3.12"
# dependencies = [
#     "pydantic>=2.12",
#     "pytest>=9.0",
# ]
# ///

# ─── How to run ───
# uv run tests/test_story_module_routing.py
# ──────────────────

from __future__ import annotations

import json
import sys
from pathlib import Path

import pytest
from pydantic import ValidationError


SKILL_ROOT = Path(__file__).resolve().parents[1]
SCRIPTS = SKILL_ROOT / "scripts"
sys.path.insert(0, str(SCRIPTS))

from story_module_models import (  # noqa: E402
    RoutingMode,
    RoutingSignalsModel,
    StoryFailureClass,
    StoryModuleId,
    StoryModuleRoutingModel,
    StoryModuleOverrideModel,
    route_story_modules,
)
from story_module_validation import (  # noqa: E402
    requires_story_module_routing,
    story_module_issues,
)


def _active_ids(routing: StoryModuleRoutingModel) -> tuple[StoryModuleId, ...]:
    return tuple(module.id for module in routing.modules if module.status == "active")


type JsonScalar = str | int | float | bool | None
type JsonValue = JsonScalar | list[JsonValue] | dict[str, JsonValue]


def _routing_payload() -> dict[str, JsonValue]:
    routing = route_story_modules(
        RoutingSignalsModel(mode=RoutingMode.NEW_EPISODE)
    )
    return {
        "schema_version": routing.schema_version,
        "policy": routing.policy,
        "mode": routing.mode.value,
        "overrides": {"enable": [], "disable": []},
        "modules": [
            {
                "id": module.id.value,
                "status": module.status.value,
                "reason": module.reason,
                "runs": module.runs,
            }
            for module in routing.modules
        ],
        "budget": {
            "max_optional_modules": routing.budget.max_optional_modules,
            "max_branch_rounds": routing.budget.max_branch_rounds,
            "max_script_rewrites": routing.budget.max_script_rewrites,
            "script_rewrites_used": routing.budget.script_rewrites_used,
        },
    }


def _brief_payload(*, policy_enabled: bool) -> dict[str, JsonValue]:
    payload: dict[str, JsonValue] = {
        "schema_version": "1.0",
        "episode_id": "EP-001",
        "title": "모듈 라우팅",
        "topic": "퇴근 후의 작은 결심",
        "topic_origin": "user",
        "audience": "일상 공감 독자",
        "tone": "가벼운 공감 유머",
        "characters": ["bgoon"],
        "directions": [
            {
                "id": identifier,
                "premise": "작은 결심이 예상 밖으로 커진다",
                "escalation": "준비가 계속 늘어난다",
                "twist": "준비만 끝나고 행동은 시작하지 못한다",
                "why_relatable": "누구나 준비를 행동처럼 느껴 본다",
            }
            for identifier in ("A", "B", "C")
        ],
        "selected_direction": "A",
        "duplicate_check": {"matched_episode_ids": [], "result": "pass"},
        "sensitivity_check": {"issues": [], "result": "pass"},
        "status": "draft",
    }
    if policy_enabled:
        payload["story_module_policy"] = "auto_with_overrides"
    return payload


def _write_json(path: Path, payload: dict[str, JsonValue]) -> None:
    _ = path.write_text(
        json.dumps(payload, ensure_ascii=False, indent=2) + "\n",
        encoding="utf-8",
    )


def test_default_new_episode_activates_only_base_story_modules() -> None:
    # Given: a new episode without optional story signals.
    signals = RoutingSignalsModel(mode=RoutingMode.NEW_EPISODE)

    # When: the story router evaluates the request.
    routing = route_story_modules(signals)

    # Then: only architecture and shot planning are active.
    assert _active_ids(routing) == (
        StoryModuleId.STORY_ARCHITECTURE,
        StoryModuleId.STORYBOARD_SHOT_PLAN,
    )


def test_serial_multi_speaker_episode_activates_both_optional_modules() -> None:
    # Given: a continuing episode with two speaking characters.
    signals = RoutingSignalsModel(
        mode=RoutingMode.NEW_EPISODE,
        serial_signal=True,
        speaker_count=2,
    )

    # When: the story router evaluates the request.
    routing = route_story_modules(signals)

    # Then: both bounded optional modules are active with the base modules.
    assert _active_ids(routing) == (
        StoryModuleId.STORY_ARCHITECTURE,
        StoryModuleId.CONTINUITY_CANON,
        StoryModuleId.DIALOGUE_PERSONA,
        StoryModuleId.STORYBOARD_SHOT_PLAN,
    )


def test_user_disable_wins_over_enable_and_automatic_selection() -> None:
    # Given: the same automatically selected module appears in both overrides.
    overrides = StoryModuleOverrideModel(
        enable=(StoryModuleId.DIALOGUE_PERSONA,),
        disable=(StoryModuleId.DIALOGUE_PERSONA,),
    )
    signals = RoutingSignalsModel(
        mode=RoutingMode.NEW_EPISODE,
        speaker_count=2,
        overrides=overrides,
    )

    # When: the story router applies precedence.
    routing = route_story_modules(signals)

    # Then: the module stays disabled and records the user decision.
    persona = next(
        module
        for module in routing.modules
        if module.id is StoryModuleId.DIALOGUE_PERSONA
    )
    assert persona.status == "skipped"
    assert persona.reason == "user_disabled"
    assert persona.runs == 0


@pytest.mark.parametrize("mode", [RoutingMode.RECOMPOSE, RoutingMode.VALIDATE])
def test_non_story_modes_load_zero_modules_even_with_force_enable(
    mode: RoutingMode,
) -> None:
    # Given: a non-story task with a conflicting enable request.
    signals = RoutingSignalsModel(
        mode=mode,
        overrides=StoryModuleOverrideModel(
            enable=(StoryModuleId.BRANCH_PAYOFF_LAB,)
        ),
    )

    # When: the story router evaluates the request.
    routing = route_story_modules(signals)

    # Then: validation and recomposition remain zero-module paths.
    assert _active_ids(routing) == ()


@pytest.mark.parametrize(
    "failure_class",
    [
        StoryFailureClass.MECHANISM,
        StoryFailureClass.BEATS,
        StoryFailureClass.PAYOFF,
        StoryFailureClass.DUPLICATE,
    ],
)
def test_typed_story_failure_activates_one_branch_round(
    failure_class: StoryFailureClass,
) -> None:
    # Given: a StoryCritic failure that needs alternate causal paths.
    signals = RoutingSignalsModel(
        mode=RoutingMode.STORY_REWRITE,
        failure_class=failure_class,
    )

    # When: the story router evaluates the failure.
    routing = route_story_modules(signals)

    # Then: the branch lab runs exactly once.
    branch = next(
        module
        for module in routing.modules
        if module.id is StoryModuleId.BRANCH_PAYOFF_LAB
    )
    assert branch.status == "active"
    assert branch.runs == 1


def test_unchanged_panel_regeneration_loads_no_story_modules() -> None:
    # Given: a visual-only panel regeneration.
    signals = RoutingSignalsModel(
        mode=RoutingMode.PANEL_REGENERATION,
        story_changed=False,
    )

    # When: the story router evaluates the request.
    routing = route_story_modules(signals)

    # Then: no story reference is loaded.
    assert _active_ids(routing) == ()


def test_routing_model_rejects_duplicate_module_entries() -> None:
    # Given: a routing record that duplicates one module and omits another.
    payload = _routing_payload()
    modules = payload["modules"]
    assert isinstance(modules, list)
    modules[-1] = modules[0]

    # When: the record crosses the JSON boundary.

    # Then: the complete unique module registry is enforced.
    with pytest.raises(ValidationError):
        _ = StoryModuleRoutingModel.model_validate(payload)


def test_routing_model_rejects_status_run_mismatch() -> None:
    # Given: an active module falsely recorded with zero runs.
    payload = _routing_payload()
    modules = payload["modules"]
    assert isinstance(modules, list)
    architecture = modules[0]
    assert isinstance(architecture, dict)
    architecture["runs"] = 0

    # When: the record crosses the JSON boundary.

    # Then: status and execution count must agree.
    with pytest.raises(ValidationError):
        _ = StoryModuleRoutingModel.model_validate(payload)


def test_routing_model_rejects_script_rewrite_budget_overrun() -> None:
    # Given: a routing record claiming a third script rewrite.
    payload = _routing_payload()
    budget = payload["budget"]
    assert isinstance(budget, dict)
    budget["script_rewrites_used"] = 3

    # When: the record crosses the JSON boundary.

    # Then: the existing two-rewrite ceiling remains binding.
    with pytest.raises(ValidationError):
        _ = StoryModuleRoutingModel.model_validate(payload)


def test_new_policy_requires_routing_record_without_retroactive_legacy_requirement(
    tmp_path: Path,
) -> None:
    # Given: one policy-enabled episode and one historical episode.
    current = tmp_path / "current"
    legacy = tmp_path / "legacy"
    current.mkdir()
    legacy.mkdir()
    _write_json(current / "brief.json", _brief_payload(policy_enabled=True))
    _write_json(legacy / "brief.json", _brief_payload(policy_enabled=False))

    # When: deterministic validation resolves both policies.
    current_required = requires_story_module_routing(current)
    legacy_required = requires_story_module_routing(legacy)
    missing_issues = story_module_issues(current)
    _write_json(current / "module-routing.json", _routing_payload())
    completed_issues = story_module_issues(current)

    # Then: only the opted-in new path requires and validates the sidecar.
    assert current_required is True
    assert legacy_required is False
    assert len(missing_issues) == 1
    assert completed_issues == ()
