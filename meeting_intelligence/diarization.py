"""Local pyannote Community-1 adapter; credentials never enter output JSON."""

from pathlib import Path

from .schemas import Turn

MODEL = "pyannote/speaker-diarization-community-1"


class DiarizationAccessError(RuntimeError):
    pass


def get_access_token(environment_root: Path) -> str | None:
    from dotenv import load_dotenv
    from huggingface_hub import get_token

    load_dotenv(environment_root / ".env", override=False)
    return get_token()


def require_access_token(environment_root: Path) -> str:
    token = get_access_token(environment_root)
    if not token:
        raise DiarizationAccessError(
            "Diarization needs model access: accept the conditions at "
            "https://huggingface.co/pyannote/speaker-diarization-community-1 "
            "and set HF_TOKEN in the environment-root .env file. "
            "Use --skip-diarization only for an explicitly unlabelled transcript."
        )
    return token


def run(
    audio_path: Path, environment_root: Path, num_speakers: int | None = None
) -> tuple[list[Turn], list[Turn]]:
    token = require_access_token(environment_root)
    import soundfile as sf
    import torch
    from pyannote.audio import Pipeline

    try:
        pipeline = Pipeline.from_pretrained(
            MODEL, token=token, cache_dir=environment_root / "models" / "huggingface"
        )
    except Exception:
        # Do not include raw HTTP/authentication exceptions in output or logs.
        raise DiarizationAccessError(
            "Could not load the diarization model. Check model access, HF_TOKEN, and network availability."
        ) from None
    if pipeline is None:
        raise DiarizationAccessError(
            "Diarization model unavailable. Check access approval and HF_TOKEN."
        )
    pipeline.to(torch.device("cpu"))
    waveform, rate = sf.read(audio_path, dtype="float32", always_2d=True)
    options = {"num_speakers": num_speakers} if num_speakers is not None else {}
    output = pipeline(
        {"waveform": torch.from_numpy(waveform.T.copy()), "sample_rate": rate}, **options
    )
    duration = len(waveform) / rate

    def convert(annotation):
        return sorted(
            [
                Turn(start=max(0, span.start), end=min(duration, span.end), speaker_id=str(speaker))
                for span, _, speaker in annotation.itertracks(yield_label=True)
                if min(duration, span.end) > max(0, span.start)
            ],
            key=lambda turn: (turn.start, turn.end),
        )

    return convert(output.speaker_diarization), convert(output.exclusive_speaker_diarization)
