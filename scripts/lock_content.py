#!/usr/bin/env -S uv run --script
# /// script
# requires-python = ">=3.12"
# dependencies = ["pydantic>=2.12", "typer>=0.20", "pillow>=12.0"]
# ///
from __future__ import annotations

from datetime import datetime
from enum import StrEnum
from pathlib import Path
from typing import Annotated

import typer
from information_lock import write_content_lock
from pydantic import ValidationError


class LockMode(StrEnum):
    USER_ACCEPTED = "user_accepted"
    AUTOMATIC_CONTRACT = "automatic_contract"


def main(
    episode_dir: Annotated[
        Path,
        typer.Option("--episode-dir", exists=True, file_okay=False, resolve_path=True),
    ],
    mode: Annotated[LockMode, typer.Option("--mode")],
    approval_note: Annotated[str, typer.Option("--approval-note", min=1)],
) -> None:
    try:
        path = write_content_lock(
            episode_dir,
            mode.value,
            approval_note,
            datetime.now().astimezone(),
        )
    except (OSError, ValueError, ValidationError) as error:
        typer.echo(f"content lock failed for {episode_dir}: {error}", err=True)
        raise typer.Exit(code=1) from error
    typer.echo(f"content locked: {path}")


if __name__ == "__main__":
    typer.run(main)
