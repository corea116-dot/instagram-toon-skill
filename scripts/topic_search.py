#!/usr/bin/env -S uv run --script
# /// script
# requires-python = ">=3.12"
# dependencies = ["pydantic>=2.12", "typer>=0.20", "pillow>=12.0"]
# ///

# How to run: uv run scripts/topic_search.py --help

from __future__ import annotations

import json
from datetime import datetime
from enum import StrEnum
from pathlib import Path
from typing import Annotated
from zoneinfo import ZoneInfo

import typer
from keyword_history import next_keyword_type
from keyword_models import (
    InformationalKeywordEvidence,
    InformationalKeywordResearch,
    KeywordEvidence,
    KeywordResearch,
    keyword_evidence_adapter,
)
from keyword_selection import select_topic
from topic_editorial import DiscoveryPool
from topic_performance import PerformanceInput, summarize_performance
from pydantic import ValidationError
from rendering import write_text_atomic

SKILL_ROOT = Path(__file__).resolve().parents[1]
DEFAULT_HISTORY = SKILL_ROOT / "memory" / "episode-history.json"
app = typer.Typer(
    help="Observed demand + compact editorial selection; local discovery and supplied-insights tools."
)


class ContentType(StrEnum):
    informational = "informational"
    humor = "humor"


@app.command()
def plan(history: Annotated[Path, typer.Option()] = DEFAULT_HISTORY, content_type: ContentType = ContentType.informational) -> None:
    """Show the next keyword type without advancing history."""
    try:
        keyword_type = next_keyword_type(history)
    except (OSError, ValidationError) as error:
        typer.echo(f"Cannot read rotation history: {error}", err=True)
        raise typer.Exit(1) from error
    typer.echo(
        json.dumps(
            {
                "requested_type": keyword_type,
                "history": str(history.resolve()),
                "audience": "20–30대 사회초년생",
                "kpi": ["조회", "신규유입"],
                "selection_policy": "editorial_v1" if content_type == ContentType.informational else "naver_monthly",
                "discovery_limit": 15,
                "shortlist_territories": "at least 3 or explicit exception",
                "ranking_metric": "AI editorial total, Naver monthly PC + mobile, stable ID" if content_type == ContentType.informational else "Naver monthly PC + mobile searches",
                "google_role": "auxiliary momentum only; never weighted",
                "candidate_count": 5,
                "collector": "aside",
                "stop_after_generation": "review_pending",
            },
            ensure_ascii=False,
            indent=2,
        )
    )


@app.command()
def schema(
    output: Annotated[Path | None, typer.Option()] = None,
    content_type: Annotated[ContentType, typer.Option()] = ContentType.informational,
) -> None:
    """Export the exact collector input schema."""
    model = (
        InformationalKeywordEvidence
        if content_type == ContentType.informational
        else KeywordEvidence
    )
    exported = model.model_json_schema()
    policy = "editorial_v1" if content_type == ContentType.informational else "naver_monthly"
    exported["properties"]["selection_policy"] = {"const": policy, "default": policy, "type": "string"}
    if content_type == ContentType.informational:
        exported["properties"]["discovery"] = {"$ref": "#/$defs/DiscoveryPool"}
        exported.setdefault("required", []).append("discovery")
        candidate = exported["$defs"]["InformationalKeywordCandidate"]
        candidate["properties"]["editorial"] = {"$ref": "#/$defs/EditorialDirection"}
        candidate.setdefault("required", []).append("editorial")
    exported.setdefault("required", []).append("selection_policy")
    content = (
        json.dumps(exported, ensure_ascii=False, indent=2)
        + "\n"
    )
    if output is None:
        typer.echo(content)
    else:
        write_text_atomic(output, content)


@app.command()
def select(
    evidence: Annotated[Path, typer.Option(exists=True, dir_okay=False)],
    output: Annotated[Path, typer.Option()],
    history: Annotated[Path, typer.Option()] = DEFAULT_HISTORY,
) -> None:
    """Validate observed evidence, rank five candidates, and write selected/hold JSON."""
    if output.exists():
        typer.echo(
            "Output already exists; choose a fresh research path (no stale-result overwrite).",
            err=True,
        )
        raise typer.Exit(1)
    try:
        payload = json.loads(evidence.read_bytes())
        if not isinstance(payload, dict):
            raise ValueError("Evidence must be a JSON object")
        # New CLI runs cannot silently fall back to historical proxy ranking.
        if payload.get("content_type") == "informational":
            if payload.get("selection_policy") != "editorial_v1":
                raise ValueError("new informational selection requires editorial_v1; use the current schema")
        else:
            payload["selection_policy"] = "naver_monthly"
        collected = keyword_evidence_adapter.validate_python(payload)
        today = datetime.now(ZoneInfo("Asia/Seoul")).date()
        if not 0 <= (today - collected.researched_on).days <= 7:
            typer.echo(
                "Evidence is future-dated or older than seven days; recollect with Aside.",
                err=True,
            )
            raise typer.Exit(1)
        decision = select_topic(collected, next_keyword_type(history))
        result = (
            InformationalKeywordResearch(evidence=collected, decision=decision)
            if isinstance(collected, InformationalKeywordEvidence)
            else KeywordResearch(evidence=collected, decision=decision)
        )
        write_text_atomic(output, result.model_dump_json(indent=2) + "\n")
    except (OSError, ValidationError, ValueError) as error:
        typer.echo(f"Cannot select a topic: {error}", err=True)
        raise typer.Exit(1) from error
    typer.echo(
        json.dumps(
            {
                "status": decision.status,
                "selected_topic": result.selected_topic,
                "creator_handoff": next((c.editorial.model_dump(mode="json") for c in collected.candidates
                                         if c.id == decision.selected_id and getattr(c, "editorial", None)), None),
                "reason": decision.reason,
                "output": str(output.resolve()),
            },
            ensure_ascii=False,
        )
    )
    if decision.status == "hold":
        raise typer.Exit(2)


@app.command("pool-schema")
def pool_schema() -> None:
    """Input schema for up to fifteen lightweight, source-backed discoveries."""
    typer.echo(json.dumps(DiscoveryPool.model_json_schema(), ensure_ascii=False, indent=2))


@app.command("pool")
def pool_command(input: Annotated[Path, typer.Option(exists=True, dir_okay=False)],
                 output: Annotated[Path, typer.Option()]) -> None:
    """Normalize duplicates, retain all reasons, and check the five-item shortlist."""
    if output.exists():
        typer.echo("Choose a fresh pool output path.", err=True)
        raise typer.Exit(1)
    try:
        data = DiscoveryPool.model_validate_json(input.read_bytes())
        report = data.normalized()
        write_text_atomic(output, json.dumps(report, ensure_ascii=False, indent=2) + "\n")
    except (OSError, ValueError) as error:
        typer.echo(str(error), err=True)
        raise typer.Exit(1) from error
    typer.echo(json.dumps({'status': report['status'], 'reasons': report['reasons'], 'output': str(output.resolve())}, ensure_ascii=False))
    if report['status'] == 'hold':
        raise typer.Exit(2)


@app.command("performance-schema")
def performance_schema() -> None:
    typer.echo(json.dumps(PerformanceInput.model_json_schema(), ensure_ascii=False, indent=2))


@app.command("performance")
def performance_command(input: Annotated[Path, typer.Option(exists=True, dir_okay=False)],
                        output: Annotated[Path, typer.Option()]) -> None:
    """Summarize supplied local insights. No network or automatic ranking weights."""
    try:
        report = summarize_performance(PerformanceInput.model_validate_json(input.read_bytes()))
        if input.resolve() == output.resolve():
            raise ValueError('input and output must differ')
        if output.exists():
            previous = json.loads(output.read_bytes())
            if previous == report:
                typer.echo('unchanged: no new insights; summary reused')
                return
            if not isinstance(previous, dict) or previous.get('use') != 'advisory_only' or previous.get('schema_version') != '1.0':
                raise ValueError('output is not an existing performance summary; choose another path')
        write_text_atomic(output, json.dumps(report, ensure_ascii=False, indent=2) + "\n")
    except (OSError, ValueError) as error:
        typer.echo(str(error), err=True)
        raise typer.Exit(1) from error
    typer.echo(str(output.resolve()))


if __name__ == "__main__":
    app()
