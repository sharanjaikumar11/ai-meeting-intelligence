"""Day 2 local transcription and speaker diarization pipeline."""

import tempfile
from pathlib import Path

from . import diarization
from .alignment import align_segments
from .media import MediaInputError, decode, ffmpeg_tools, is_digital_silence, probe_media
from .schemas import Speaker, Transcript


def transcription_quality_warnings(segments):
    """Conservative review signal; Whisper probabilities are not calibrated accuracy."""
    probabilities = [
        word.probability
        for segment in segments
        for word in segment.words
        if word.probability is not None
    ]
    low = sum(p < 0.35 for p in probabilities)
    if len(probabilities) >= 10 and low / len(probabilities) >= 0.20:
        return [
            f"Transcription needs review: {low} of {len(probabilities)} words have Whisper probability below 0.35. This is an uncalibrated uncertainty heuristic, not an accuracy score. Noise or unclear speech may create incorrect words; verify the audio before relying on extracted tasks or decisions."
        ]
    return []


def transcribe(
    source: Path,
    environment_root: Path,
    model_name: str = "small",
    language: str = "en",
    start: float = 0,
    duration: float | None = None,
    skip_diarization: bool = False,
    num_speakers: int | None = None,
    speaker_names: dict[str, str] | None = None,
    threads: int = 4,
    diarization_context: float = 0,
    beam_size: int | None = None,
) -> Transcript:
    import math

    if beam_size is not None and (type(beam_size) is not int or beam_size < 1):
        raise ValueError("Beam size must be a positive integer or omitted.")
    if (
        not math.isfinite(start)
        or start < 0
        or duration is not None
        and (not math.isfinite(duration) or duration <= 0)
    ):
        raise ValueError("Start must be nonnegative and duration must be positive and finite.")
    if threads < 1 or num_speakers is not None and num_speakers < 1:
        raise ValueError("Threads and speaker count must be positive integers.")
    if not math.isfinite(diarization_context) or diarization_context < 0:
        raise ValueError("Diarization context must be nonnegative and finite.")
    if skip_diarization and (speaker_names or num_speakers is not None):
        raise ValueError("Speaker mapping/count cannot be used with skipped diarization.")
    ffmpeg, ffprobe = ffmpeg_tools(environment_root)
    media = probe_media(source, ffprobe)
    if start >= media["duration"]:
        raise MediaInputError("Start offset must be before the end of the recording.")
    import torch
    import whisper

    if model_name not in whisper.available_models():
        raise ValueError(f"Unknown Whisper model: {model_name}")
    torch.set_num_threads(threads)
    torch.manual_seed(0)
    requested_duration = min(
        duration if duration is not None else media["duration"] - start, media["duration"] - start
    )
    with tempfile.TemporaryDirectory(prefix="meeting-audio-") as folder:
        wav = Path(folder) / "audio.wav"
        actual_duration = decode(
            source, wav, ffmpeg, media["audio_stream_index"], start, requested_duration
        )
        if is_digital_silence(wav):
            return Transcript(
                source_file=str(source.resolve()),
                source_duration_seconds=media["duration"],
                processed_start_seconds=start,
                processed_duration_seconds=actual_duration,
                language=language,
                asr_model="not_run_digital_silence",
                diarization_model=None,
                diarization_status="skipped",
                text="",
                speakers=[],
                segments=[],
                diarization_turns=[],
                exclusive_diarization_turns=[],
                warnings=[
                    "The selected interval contains only digital silence (all PCM samples are zero). Transcription and diarization were skipped; no speech was invented."
                ],
            )
        if not skip_diarization:
            diarization.require_access_token(environment_root)
        print(f"Audio prepared: {actual_duration:.2f}s; loading Whisper {model_name}", flush=True)
        model = whisper.load_model(
            model_name, device="cpu", download_root=str(environment_root / "models" / "whisper")
        )
        decoding = {"beam_size": beam_size} if beam_size is not None else {}
        result = model.transcribe(
            str(wav),
            language=language if language != "auto" else None,
            task="transcribe",
            fp16=False,
            word_timestamps=True,
            temperature=0,
            condition_on_previous_text=False,
            verbose=None,
            **decoding,
        )
        del model
        regular, exclusive = [], []
        if not skip_diarization:
            print("Transcription finished; running speaker diarization", flush=True)
            if diarization_context:
                context_start = max(0, start - diarization_context)
                context_end = min(media["duration"], start + actual_duration + diarization_context)
                context_wav = Path(folder) / "speaker-context.wav"
                decode(
                    source,
                    context_wav,
                    ffmpeg,
                    media["audio_stream_index"],
                    context_start,
                    context_end - context_start,
                )
                regular, exclusive = diarization.run(context_wav, environment_root, num_speakers)
                regular = crop_turns(regular, start - context_start, actual_duration)
                exclusive = crop_turns(exclusive, start - context_start, actual_duration)
            else:
                regular, exclusive = diarization.run(wav, environment_root, num_speakers)
    speaker_ids = sorted({turn.speaker_id for turn in regular + exclusive})
    speaker_names = speaker_names or {}
    if set(speaker_names) - set(speaker_ids):
        raise ValueError("Speaker-name mapping contains IDs not detected in this recording.")
    segments = align_segments(
        result["segments"], exclusive, regular, actual_duration, start, speaker_names
    )
    warnings = [
        "Timestamps and speaker assignments are model estimates. Speaker IDs are local to this recording."
    ]
    if beam_size is not None:
        warnings.append(
            f"Whisper used beam size {beam_size}; this optional decoding setting is not a guarantee of higher accuracy."
        )
    warnings.extend(transcription_quality_warnings(segments))
    if not skip_diarization and num_speakers is not None:
        warnings.append(
            f"Diarization used a supplied speaker count of {num_speakers}; this is not an automatic count estimate."
        )
    if not skip_diarization and diarization_context:
        warnings.append(
            f"Diarization used up to {diarization_context:g} seconds of surrounding audio per side, then cropped turns to this transcript interval."
        )
    if skip_diarization:
        warnings.append("Diarization was explicitly skipped; all speakers remain unassigned.")
    elif any(segment.speaker_id is None for segment in segments):
        warnings.append("Some speech could not be assigned to a speaker unambiguously.")
    if any(segment.overlapping_speech for segment in segments):
        warnings.append(
            "Overlapping speech detected; a single transcript may omit simultaneous words."
        )
    return Transcript(
        source_file=str(source.resolve()),
        source_duration_seconds=media["duration"],
        processed_start_seconds=start,
        processed_duration_seconds=actual_duration,
        language=result["language"],
        asr_model=model_name,
        diarization_model=None if skip_diarization else diarization.MODEL,
        diarization_status="skipped" if skip_diarization else "completed",
        text=result["text"].strip(),
        segments=segments,
        speakers=[
            Speaker(
                id=speaker,
                name=speaker_names.get(speaker),
                name_source="user_provided" if speaker in speaker_names else None,
            )
            for speaker in speaker_ids
        ],
        diarization_turns=[
            turn.model_copy(update={"start": turn.start + start, "end": turn.end + start})
            for turn in regular
        ],
        exclusive_diarization_turns=[
            turn.model_copy(update={"start": turn.start + start, "end": turn.end + start})
            for turn in exclusive
        ],
        warnings=warnings,
    )


def crop_turns(turns, offset, duration):
    """Crop context turns and shift them into the transcribed excerpt's local clock."""
    return [
        t.model_copy(
            update={"start": max(0, t.start - offset), "end": min(duration, t.end - offset)}
        )
        for t in turns
        if t.end > offset and t.start < offset + duration
    ]
