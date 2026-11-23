"""Day 3 structured summaries and their transcript evidence."""

from typing import Literal

from pydantic import BaseModel, ConfigDict, Field

from .schemas import Span


class StrictModel(BaseModel):
    model_config = ConfigDict(extra="forbid", str_strip_whitespace=True)


class EvidenceReference(StrictModel):
    segment_id: str = Field(min_length=1)


class SummaryClaim(StrictModel):
    text: str = Field(min_length=1, max_length=1200)
    evidence: list[EvidenceReference] = Field(min_length=1, max_length=8)


class DiscussionPoint(StrictModel):
    topic: str = Field(min_length=1, max_length=160)
    detail: str = Field(min_length=1, max_length=1600)
    evidence: list[EvidenceReference] = Field(min_length=1, max_length=8)


class GeneratedNotes(StrictModel):
    summary: list[SummaryClaim] = Field(min_length=1, max_length=8)
    key_discussion_points: list[DiscussionPoint] = Field(max_length=12)


class Evidence(Span):
    segment_id: str
    quote: str
    speaker_id: str | None


class SupportedClaim(StrictModel):
    text: str
    evidence: list[Evidence]


class SupportedDiscussionPoint(StrictModel):
    topic: str
    detail: str
    evidence: list[Evidence]


class MeetingSummary(StrictModel):
    schema_version: str = "1.0"
    prompt_version: str = "day08-summary-v6"
    generation_status: Literal["generated", "no_speech"]
    input_scope: Literal["full_recording", "excerpt"]
    processed_interval: Span
    source_transcript_sha256: str
    model: str
    model_version: str | None = None
    meeting_summary: str
    summary_statements: list[SupportedClaim]
    key_discussion_points: list[SupportedDiscussionPoint]
    warnings: list[str]
    usage: dict[str, int] = Field(default_factory=dict)
