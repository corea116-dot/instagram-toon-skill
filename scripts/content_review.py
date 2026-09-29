"""Validate review records, not the truth or meaning of an episode.

An independent reviewer supplies semantic judgments after a blind script read.
This module checks the record, quoted panel evidence, coverage, and input hashes.
"""
from __future__ import annotations

import hashlib
import json
from pathlib import Path
from typing import Annotated, Literal, Self

from pydantic import AwareDatetime, Field, StringConstraints, ValidationError, model_validator

from episode_models import BriefModel, EpisodeScriptModel, NonBlankString, StrictModel

Sha256 = Annotated[str, StringConstraints(pattern=r"^[0-9a-f]{64}$")]


class BlindReadModel(StrictModel):
    completed_at: AwareDatetime
    topic_understood: NonBlankString
    learned: NonBlankString
    next_action: NonBlankString


class ReviewCheckModel(StrictModel):
    passed: bool
    evidence: NonBlankString


class ContentChecksModel(StrictModel):
    answers_reader_question: ReviewCheckModel
    topic_specificity: ReviewCheckModel
    claims_sources_conditions: ReviewCheckModel
    benefits_conditions_risks: ReviewCheckModel
    standalone_comprehension: ReviewCheckModel
    dialogue_numbers_continuity: ReviewCheckModel


class ClaimCoverageModel(StrictModel):
    fact_id: NonBlankString
    panel: Annotated[int, Field(ge=1)]
    script_quote: NonBlankString
    source_urls: Annotated[tuple[NonBlankString, ...], Field(min_length=1)]
    assessment: NonBlankString


class ContentReviewModel(StrictModel):
    schema_version: Literal["1.0"]
    episode_id: NonBlankString
    writer_id: NonBlankString
    reviewer_id: NonBlankString
    brief_sha256: Sha256
    script_sha256: Sha256
    stages: tuple[Literal["blind_read"], Literal["card_source_checks"]]
    blind_read: BlindReadModel
    checked_at: AwareDatetime
    checks: ContentChecksModel
    claim_coverage: Annotated[tuple[ClaimCoverageModel, ...], Field(min_length=1)]
    review_round: Annotated[int, Field(ge=1, le=3)] = 1
    additional_review_reason: NonBlankString | None = None
    outcome: Literal["pass", "fail"]

    @model_validator(mode="after")
    def review_contract(self) -> Self:
        if self.writer_id == self.reviewer_id:
            raise ValueError("content review requires a reviewer different from the writer")
        if self.checked_at <= self.blind_read.completed_at:
            raise ValueError("card/source checks must follow the blind read")
        if self.review_round > 1 and self.additional_review_reason is None:
            raise ValueError("additional reviews require a reason")
        all_pass = all(check["passed"] for check in self.checks.model_dump().values())
        if (self.outcome == "pass") != all_pass:
            raise ValueError("review outcome must match all six hard checks")
        return self


def file_sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def content_review_issues(episode_dir: Path) -> tuple[str, ...]:
    """Legacy episodes need no new review. Malformed informational records fail closed."""
    brief_path = episode_dir / "brief.json"
    if not brief_path.is_file():
        return ()
    try:
        payload = json.loads(brief_path.read_text(encoding="utf-8"))
        if not isinstance(payload, dict):
            return ("content review: brief.json must contain an object",)
        if payload.get("content_type") != "informational" and payload.get("schema_version") != "1.2":
            return ()
        brief = BriefModel.model_validate(payload)
        script_path = episode_dir / "script.json"
        script = EpisodeScriptModel.model_validate_json(script_path.read_text(encoding="utf-8"))
        review_path = episode_dir / "content-review.json"
        review = ContentReviewModel.model_validate_json(review_path.read_text(encoding="utf-8"))
    except (OSError, UnicodeError, ValueError, ValidationError) as error:
        return (f"content review: {error}",)
    issues: list[str] = []
    if review.outcome != "pass":
        issues.append("content review has not passed all six hard checks")
    if review.brief_sha256 != file_sha256(brief_path) or review.script_sha256 != file_sha256(script_path):
        issues.append("content review is stale: brief/script SHA-256 mismatch")
    if review.episode_id != brief.episode_id or brief.episode_id != script.episode_id:
        issues.append("content review, brief and script episode IDs must match")
    if brief.title != script.title or brief.output_layout != script.output_layout:
        issues.append("informational brief and script title/output_layout must match")
    if brief.duplicate_check.result != "pass" or brief.sensitivity_check.result != "pass":
        issues.append("informational duplicate and sensitivity checks must pass")
    assert brief.question_answer is not None
    facts = {fact.id: fact for fact in brief.question_answer.required_facts}
    covered = {coverage.fact_id for coverage in review.claim_coverage}
    if covered != set(facts):
        issues.append("content review claim coverage must cover every required fact and no unknown fact")
    for coverage in review.claim_coverage:
        if coverage.panel > len(script.panels):
            issues.append(f"content review references missing panel {coverage.panel}")
            continue
        panel = script.panels[coverage.panel - 1]
        visible_text = "\n".join(line.text for line in panel.dialogue)
        if coverage.script_quote not in visible_text:
            issues.append(f"content review quote is absent from panel {coverage.panel} dialogue")
        fact = facts.get(coverage.fact_id)
        if fact is not None:
            known_urls = {str(source.url) for source in fact.sources}
            if not set(coverage.source_urls).issubset(known_urls):
                issues.append(f"content review has unknown source for fact {coverage.fact_id}")
    return tuple(issues)


def require_content_review(episode_dir: Path) -> None:
    issues = content_review_issues(episode_dir)
    if issues:
        raise ValueError("; ".join(issues))
