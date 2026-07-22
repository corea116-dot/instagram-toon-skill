from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path


AGENT_MARKER = "## Agent QA"


@dataclass(frozen=True, slots=True)
class QaSupplemental:
    advisory_findings: tuple[str, ...] = ()
    story_modules: tuple[str, ...] = ()


def existing_agent_section(report_path: Path) -> str:
    if not report_path.is_file():
        return ""
    existing = report_path.read_text(encoding="utf-8")
    marker_at = existing.find(AGENT_MARKER)
    return existing[marker_at:].strip() if marker_at >= 0 else ""


def qa_report_text(
    issues: tuple[str, ...], agent_section: str, supplemental: QaSupplemental
) -> str:
    status = "FAIL" if issues else "PASS"
    checks = (
        "\n".join(f"- {issue}" for issue in issues)
        if issues
        else "- required files: pass\n- JSON schemas: pass\n- PNG dimensions and decoding: pass\n- speech-bubble bounds: pass"
    )
    parts = (
        "# QA Report",
        "",
        f"Automated validation: **{status}**",
        "",
        "## Automated checks",
        "",
        checks,
    )
    report = "\n".join(parts).rstrip() + "\n"
    if supplemental.advisory_findings:
        report += (
            "\n## Advisory review findings\n\n"
            + "\n".join(
                f"- {finding}" for finding in supplemental.advisory_findings
            )
            + "\n"
        )
    if supplemental.story_modules:
        report += (
            "\n## Story modules\n\n"
            + "\n".join(f"- {item}" for item in supplemental.story_modules)
            + "\n"
        )
    return report + ("\n" + agent_section + "\n" if agent_section else "")
