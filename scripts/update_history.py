#!/usr/bin/env -S uv run --script
# /// script
# requires-python = ">=3.12"
# dependencies = [
#     "pydantic>=2.12",
#     "typer>=0.20",
#     "pillow>=12.0",
# ]
# ///

# ─── How to run ───
# 1. Install uv (if not installed):
#      curl -LsSf https://astral.sh/uv/install.sh | sh
# 2. Run directly (no venv, no pip install needed):
#      uv run scripts/update_history.py \
#        --episode-dir episodes/EP-001-title --status draft
# 3. Or make executable and run:
#      chmod +x scripts/update_history.py
#      ./scripts/update_history.py \
#        --episode-dir episodes/EP-001-title --status draft
# ─────────────────

from __future__ import annotations

import os
import tempfile
from dataclasses import dataclass
from datetime import UTC, datetime
from enum import StrEnum
from pathlib import Path
from typing import Annotated, ClassVar, Literal, TypeVar, override

import typer
from content_review import require_content_review
from episode_models import EpisodeScriptModel
from keyword_history import KeywordCompletion, completion_for_episode
from pydantic import BaseModel, ConfigDict, Field, ValidationError
from pydantic_core import PydanticCustomError

SKILL_ROOT = Path(__file__).resolve().parents[1]
DEFAULT_HISTORY = SKILL_ROOT / "memory" / "episode-history.json"


class _EpisodeStatus(StrEnum):
    DRAFT = "draft"
    APPROVED = "approved"
    PUBLISHED = "published"


class _BriefModel(BaseModel):
    model_config: ClassVar[ConfigDict] = ConfigDict(frozen=True)

    schema_version: Literal["1.0", "1.1", "1.2"]
    content_type: Literal["humor", "informational"] = "humor"
    episode_id: str = Field(min_length=1)
    title: str = Field(min_length=1)
    topic: str = Field(min_length=1)
    premise: str | None = None
    twist: str | None = None
    characters: tuple[str, ...]
    created_at: str | None = None
    selected_humor_engine_id: str | None = None
    selected_beat_signature: str | None = None
    hook_mode: str | None = None
    topic_origin: str = "user"


class _HistoryEntryModel(BaseModel):
    model_config: ClassVar[ConfigDict] = ConfigDict(frozen=True, extra="allow")

    episode_id: str = Field(min_length=1)
    title: str = Field(min_length=1)
    topic: str = Field(min_length=1)
    premise: str = Field(min_length=1)
    twist: str = Field(min_length=1)
    characters: tuple[str, ...]
    path: str = Field(min_length=1)
    created_at: str = Field(min_length=1)
    status: _EpisodeStatus
    content_type: Literal["humor", "informational"] = "humor"
    humor_engine_id: str | None = None
    beat_signature: str | None = None
    hook_mode: str | None = None
    keyword_selection: KeywordCompletion | None = None


class _HistoryModel(BaseModel):
    model_config: ClassVar[ConfigDict] = ConfigDict(frozen=True, extra="allow")

    schema_version: Literal["1.0", "1.1"]
    episodes: tuple[_HistoryEntryModel, ...]


_ModelT = TypeVar("_ModelT", bound=BaseModel)


@dataclass(frozen=True, slots=True)
class _InputFileError(Exception):
    path: Path
    detail: str

    @override
    def __str__(self) -> str:
        return f"cannot parse {self.path}: {self.detail}"


@dataclass(frozen=True, slots=True)
class _EpisodeDataError(Exception):
    detail: str

    @override
    def __str__(self) -> str:
        return self.detail


def _read_model(path: Path, model_type: type[_ModelT]) -> _ModelT:
    try:
        return model_type.model_validate_json(path.read_text(encoding="utf-8"))
    except (OSError, UnicodeError, ValidationError) as error:
        raise _InputFileError(path=path, detail=str(error)) from error


def _update_history(
    episode_dir: Path,
    history_path: Path,
    status: _EpisodeStatus,
) -> Path:
    brief = _read_model(episode_dir / "brief.json", _BriefModel)
    script = _read_model(episode_dir / "script.json", EpisodeScriptModel)
    try:
        require_content_review(episode_dir)
    except ValueError as error:
        raise _EpisodeDataError(f"content review blocked history: {error}") from error
    history = _read_model(history_path, _HistoryModel)
    try:
        keyword_selection = completion_for_episode(episode_dir, brief.topic_origin)
    except (OSError, ValidationError, PydanticCustomError) as error:
        raise _EpisodeDataError(f"keyword completion blocked: {error}") from error
    if brief.content_type == "informational" and keyword_selection is None:
        from validate_episode import validate_episode

        _, issues = validate_episode(episode_dir)
        if issues:
            raise _EpisodeDataError(
                "informational completion blocked: " + "; ".join(issues)
            )

    if brief.episode_id != script.episode_id:
        detail = (
            "brief.json and script.json disagree on episode_id: "
            f"{brief.episode_id!r} != {script.episode_id!r}"
        )
        raise _EpisodeDataError(detail)
    if brief.title != script.title:
        detail = (
            "brief.json and script.json disagree on title: "
            f"{brief.title!r} != {script.title!r}"
        )
        raise _EpisodeDataError(detail)

    final_panel = script.panels[-1]
    if final_panel.panel != len(script.panels):
        detail = (
            f"script.json panel {len(script.panels)} is missing; "
            f"found panel {final_panel.panel} last"
        )
        raise _EpisodeDataError(detail)

    episode_path = episode_dir.resolve()
    try:
        history_root = history_path.resolve().parent.parent
        stored_path = str(episode_path.relative_to(history_root))
    except ValueError:
        stored_path = str(episode_path)

    dialogue_twist = " / ".join(line.text.strip() for line in final_panel.dialogue)
    created_at = brief.created_at or datetime.now(UTC).isoformat(timespec="seconds")
    incoming = _HistoryEntryModel(
        episode_id=brief.episode_id,
        title=brief.title,
        topic=brief.topic,
        premise=brief.premise or brief.topic,
        twist=brief.twist or dialogue_twist or final_panel.action,
        characters=brief.characters,
        path=stored_path,
        created_at=created_at,
        status=status,
        content_type=brief.content_type,
        humor_engine_id=brief.selected_humor_engine_id,
        beat_signature=brief.selected_beat_signature,
        hook_mode=brief.hook_mode,
        keyword_selection=keyword_selection,
    )

    entries: list[_HistoryEntryModel] = []
    replaced = False
    for entry in history.episodes:
        if entry.episode_id != brief.episode_id:
            entries.append(entry)
            continue
        if entry.title != brief.title:
            detail = (
                f"episode {brief.episode_id} already has title {entry.title!r}; "
                f"refusing incoming title {brief.title!r}"
            )
            raise _EpisodeDataError(detail)
        if replaced:
            continue
        entries.append(
            entry.model_copy(
                update={
                    "topic": incoming.topic,
                    "premise": incoming.premise,
                    "twist": incoming.twist,
                    "characters": incoming.characters,
                    "path": incoming.path,
                    "status": incoming.status,
                    "content_type": incoming.content_type,
                    "humor_engine_id": incoming.humor_engine_id,
                    "beat_signature": incoming.beat_signature,
                    "hook_mode": incoming.hook_mode,
                    "keyword_selection": incoming.keyword_selection or entry.keyword_selection,
                },
            ),
        )
        replaced = True
    if not replaced:
        entries.append(incoming)

    updated = history.model_copy(
        update={
            "schema_version": "1.1"
            if brief.schema_version in ("1.1", "1.2")
            else history.schema_version,
            "episodes": tuple(entries),
        }
    )
    payload = updated.model_dump_json(indent=2) + "\n"
    with tempfile.TemporaryDirectory(
        prefix=f".{history_path.name}.",
        dir=history_path.parent,
    ) as temp_dir:
        temporary_path = Path(temp_dir) / history_path.name
        with temporary_path.open("w", encoding="utf-8") as stream:
            _ = stream.write(payload)
            stream.flush()
            os.fsync(stream.fileno())
        _ = temporary_path.replace(history_path)
    return history_path.resolve()


def main(
    episode_dir: Annotated[
        Path,
        typer.Option("--episode-dir", exists=True, file_okay=False, readable=True),
    ],
    status: Annotated[_EpisodeStatus, typer.Option("--status")],
    history: Annotated[
        Path,
        typer.Option("--history", exists=True, dir_okay=False, readable=True),
    ] = DEFAULT_HISTORY,
) -> None:
    """Upsert one episode through the command-line interface."""
    try:
        result_path = _update_history(
            episode_dir,
            history,
            status,
        )
    except (
        _EpisodeDataError,
        _InputFileError,
        OSError,
    ) as error:
        typer.echo(f"error: {error}", err=True)
        raise typer.Exit(code=1) from error

    typer.echo(result_path)


if __name__ == "__main__":
    typer.run(main)
