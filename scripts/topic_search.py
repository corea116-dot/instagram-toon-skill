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
from pydantic import ValidationError
from rendering import write_text_atomic

SKILL_ROOT = Path(__file__).resolve().parents[1]
DEFAULT_HISTORY = SKILL_ROOT / "memory" / "episode-history.json"
app = typer.Typer(
    help="Aside evidence → reproducible Naver 60% / Google 40% topic selection."
)


class ContentType(StrEnum):
    informational = "informational"
    humor = "humor"


@app.command()
def plan(history: Annotated[Path, typer.Option()] = DEFAULT_HISTORY) -> None:
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
                "weights": {"naver": 0.6, "google": 0.4},
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
    content = (
        json.dumps(model.model_json_schema(), ensure_ascii=False, indent=2)
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
        collected = keyword_evidence_adapter.validate_json(evidence.read_bytes())
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
    except (OSError, ValidationError) as error:
        typer.echo(f"Cannot select a topic: {error}", err=True)
        raise typer.Exit(1) from error
    typer.echo(
        json.dumps(
            {
                "status": decision.status,
                "selected_topic": result.selected_topic,
                "reason": decision.reason,
                "output": str(output.resolve()),
            },
            ensure_ascii=False,
        )
    )
    if decision.status == "hold":
        raise typer.Exit(2)


if __name__ == "__main__":
    app()
