"""Day 4 action, owner, deadline, and pending-question structures."""

from datetime import date
from typing import Literal

from pydantic import Field, model_validator

from .schemas import Span
from .summary_schemas import Evidence, EvidenceReference, StrictModel


class GeneratedOwner(StrictModel):
    kind: Literal["person", "role", "group", "self", "unknown"]
    mention: str | None = Field(
        description="Exact owner phrase in evidence; I for a first-person commitment; null if unknown."
    )
    evidence: list[EvidenceReference] = Field(max_length=8)

    @model_validator(mode="after")
    def consistent(self):
        if self.kind == "unknown":
            if self.mention is not None or self.evidence:
                raise ValueError("Unknown owner must have null mention and no owner evidence")
        elif not self.mention or not self.evidence:
            raise ValueError("Known owner requires an exact mention and evidence")
        return self


class GeneratedDeadline(StrictModel):
    text: str | None = Field(
        description="One exact deadline phrase from a cited segment; null if no deadline is established."
    )
    evidence: list[EvidenceReference] = Field(max_length=8)

    @model_validator(mode="after")
    def consistent(self):
        if self.text is None and self.evidence:
            raise ValueError("Missing deadline cannot have deadline evidence")
        if self.text is not None and (not self.text or not self.evidence):
            raise ValueError("Deadline phrase requires evidence")
        return self


class GeneratedAction(StrictModel):
    task: str = Field(min_length=1, max_length=1200)
    assignment_type: Literal["assignment", "commitment", "suggestion"]
    evidence: list[EvidenceReference] = Field(min_length=1, max_length=12)
    owner: GeneratedOwner
    deadline: GeneratedDeadline


class GeneratedQuestion(StrictModel):
    question: str = Field(min_length=1, max_length=1200)
    evidence: list[EvidenceReference] = Field(min_length=1, max_length=12)


class GeneratedActions(StrictModel):
    action_items: list[GeneratedAction] = Field(max_length=100)
    pending_questions: list[GeneratedQuestion] = Field(max_length=100)


class Owner(StrictModel):
    kind: Literal["person", "role", "group", "self", "unknown"]
    mention: str | None
    responsible_person: str | None
    speaker_id: str | None
    evidence: list[Evidence]
    resolution_note: str | None


class Deadline(StrictModel):
    text: str | None
    date_iso: date | None
    resolution: Literal["missing", "absolute_date", "relative_date", "unresolved"]
    resolution_note: str | None
    evidence: list[Evidence]


class Action(StrictModel):
    id: str
    task: str
    assignment_type: Literal["assignment", "commitment", "suggestion"]
    evidence: list[Evidence]
    owner: Owner
    deadline: Deadline


class PendingQuestion(StrictModel):
    id: str
    question: str
    status: Literal["unresolved_in_supplied_transcript"] = "unresolved_in_supplied_transcript"
    evidence: list[Evidence]


class MeetingActions(StrictModel):
    schema_version: str = "1.0"
    prompt_version: str = "day10-actions-v7"
    generation_status: Literal["generated", "no_speech"]
    input_scope: Literal["full_recording", "excerpt"]
    processed_interval: Span
    meeting_date: date | None
    source_transcript_sha256: str
    model: str
    model_version: str | None = None
    action_items: list[Action]
    pending_questions: list[PendingQuestion]
    warnings: list[str]
    usage: dict[str, int] = Field(default_factory=dict)
