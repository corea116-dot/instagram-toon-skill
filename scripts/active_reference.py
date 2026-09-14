#!/usr/bin/env -S uv run --script
# /// script
# requires-python = ">=3.12"
# dependencies = [
#     "pillow>=12.0",
#     "pydantic>=2.12",
#     "typer>=0.20",
# ]
# ///

from __future__ import annotations

import json
from pathlib import Path

from reference_policy import ACTIVE_REFERENCE_MARKER, resolve_reference_paths
from rendering import RenderError

SKILL_ROOT = Path(__file__).resolve().parents[1]


def main() -> None:
    try:
        references = resolve_reference_paths(
            (ACTIVE_REFERENCE_MARKER,), SKILL_ROOT, "active reference"
        )
    except RenderError as error:
        raise SystemExit(str(error)) from error
    print(
        json.dumps(
            {
                "reference_images": references,
                "absolute_paths": tuple(
                    str(SKILL_ROOT / reference) for reference in references
                ),
            }
        )
    )


if __name__ == "__main__":
    main()
