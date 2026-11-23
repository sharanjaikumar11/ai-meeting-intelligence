"""Validated Day 2 transcription output."""

from typing import Literal

from pydantic import BaseModel, ConfigDict, Field, FiniteFloat, model_validator


class Span(BaseModel):
    model_config = ConfigDict(extra="forbid")
    start: FiniteFloat = Field(ge=0)
    end: FiniteFloat = Field(ge=0)

    @model_validator(mode="after")
    def ordered(self):
        if self.end < self.start:
            raise ValueError("End timestamp precedes start timestamp")
        return self


class Turn(Span):
    speaker_id: str


class Word(Span):
    text: str
    probability: FiniteFloat | None = Field(default=None, ge=0, le=1)
    speaker_id: str | None = None
    overlapping_speech: bool = False


class Segment(Span):
    id: str
    source_segment_id: str
    text: str
    speaker_id: str | None = None
    speaker_name: str | None = None
    overlapping_speech: bool = False
    words: list[Word] = Field(default_factory=list)


class Speaker(BaseModel):
    id: str
    name: str | None = None
    name_source: Literal["user_provided"] | None = None


class Transcript(BaseModel):
    schema_version: str = "1.0"
    source_file: str
    source_duration_seconds: FiniteFloat = Field(gt=0)
    processed_start_seconds: FiniteFloat = Field(ge=0)
    processed_duration_seconds: FiniteFloat = Field(gt=0)
    timestamp_basis: Literal["original_input_seconds"] = "original_input_seconds"
    language: str
    asr_model: str
    diarization_model: str | None
    diarization_status: Literal["completed", "skipped"]
    text: str
    speakers: list[Speaker]
    segments: list[Segment]
    diarization_turns: list[Turn]
    exclusive_diarization_turns: list[Turn]
    warnings: list[str] = Field(default_factory=list)

    @model_validator(mode="after")
    def valid_timeline(self):
        lower = self.processed_start_seconds
        upper = lower + self.processed_duration_seconds
        if upper > self.source_duration_seconds + 0.1:
            raise ValueError("Processed interval exceeds source duration")
        known = {speaker.id for speaker in self.speakers}
        if len(known) != len(self.speakers):
            raise ValueError("Duplicate speaker IDs")
        if len({segment.id for segment in self.segments}) != len(self.segments):
            raise ValueError("Duplicate segment IDs")
        previous_start = lower
        for segment in self.segments:
            if segment.start < previous_start:
                raise ValueError("Segments must be ordered by start time")
            previous_start = segment.start
            if segment.start < lower - 0.001 or segment.end > upper + 0.001:
                raise ValueError("Segment outside processed interval")
            if segment.speaker_id is not None and segment.speaker_id not in known:
                raise ValueError("Unknown speaker reference")
            for word in segment.words:
                if word.start < segment.start - 0.001 or word.end > segment.end + 0.001:
                    raise ValueError("Word outside segment")
                if word.speaker_id != segment.speaker_id:
                    raise ValueError("Word and segment speaker disagree")
        for turn in self.diarization_turns + self.exclusive_diarization_turns:
            if (
                turn.start < lower - 0.001
                or turn.end > upper + 0.001
                or turn.speaker_id not in known
            ):
                raise ValueError("Invalid diarization turn")
        if self.diarization_status == "skipped" and (
            known or self.diarization_turns or self.exclusive_diarization_turns
        ):
            raise ValueError("Skipped diarization cannot contain predicted speakers")
        return self
