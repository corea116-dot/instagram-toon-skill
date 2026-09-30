"""Bind an informational script decision to its reviewed semantic content."""

from __future__ import annotations

from datetime import datetime
from pathlib import Path
from typing import Literal

from content_review import require_content_review, semantic_content_sha256
from episode_models import BriefModel, NonBlankString, StrictModel
from pydantic import AwareDatetime, ValidationError
from rendering import write_text_atomic


class ContentLockModel(StrictModel):
    schema_version: Literal["1.0"]
    episode_id: NonBlankString
    content_sha256: NonBlankString
    mode: Literal["user_accepted", "automatic_contract"]
    locked_at: AwareDatetime
    approval_note: NonBlankString


def _modern_information_brief(episode_dir: Path) -> BriefModel | None:
    path = episode_dir / "brief.json"
    if not path.is_file():
        return None
    try:
        brief = BriefModel.model_validate_json(path.read_text(encoding="utf-8"))
    except (OSError, ValidationError):
        return None
    if brief.content_type == "informational" and brief.schema_version == "1.3":
        return brief
    return None


def content_lock_issues(episode_dir: Path) -> tuple[str, ...]:
    brief = _modern_information_brief(episode_dir)
    if brief is None:
        return ()
    path = episode_dir / "content-lock.json"
    try:
        lock = ContentLockModel.model_validate_json(path.read_text(encoding="utf-8"))
    except (OSError, ValidationError) as error:
        return (f"content lock: {error}",)
    issues: list[str] = []
    if lock.episode_id != brief.episode_id:
        issues.append("content lock episode_id does not match the brief")
    try:
        current_hash = semantic_content_sha256(
            episode_dir / "brief.json", episode_dir / "script.json"
        )
    except (OSError, ValidationError, ValueError) as error:
        issues.append(f"content lock cannot hash current content: {error}")
    else:
        if lock.content_sha256 != current_hash:
            issues.append("content lock is stale: semantic content SHA-256 mismatch")
    return tuple(issues)


def require_content_lock(episode_dir: Path) -> None:
    issues = content_lock_issues(episode_dir)
    if issues:
        raise ValueError("; ".join(issues))


def write_content_lock(
    episode_dir: Path,
    mode: Literal["user_accepted", "automatic_contract"],
    approval_note: str,
    locked_at: datetime,
) -> Path:
    require_content_review(episode_dir)
    brief = _modern_information_brief(episode_dir)
    if brief is None:
        raise ValueError(
            "content lock is only required for informational brief schema 1.3"
        )
    lock = ContentLockModel(
        schema_version="1.0",
        episode_id=brief.episode_id,
        content_sha256=semantic_content_sha256(
            episode_dir / "brief.json", episode_dir / "script.json"
        ),
        mode=mode,
        locked_at=locked_at,
        approval_note=approval_note,
    )
    path = episode_dir / "content-lock.json"
    write_text_atomic(path, lock.model_dump_json(indent=2) + "\n")
    return path
