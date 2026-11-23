"""Decode a local audio or video file into a temporary 16-kHz mono WAV."""

import json
import os
import shutil
import subprocess
import wave
from pathlib import Path


class MediaInputError(ValueError):
    """Safe, actionable recording validation message for the local interface."""


def is_digital_silence(wav: Path) -> bool:
    """Only exact zero PCM samples qualify; quiet or noisy signals are not removed."""
    with wave.open(str(wav)) as audio:
        if audio.getsampwidth() != 2 or audio.getcomptype() != "NONE":
            raise ValueError("Digital-silence check requires decoded 16-bit PCM.")
        if audio.getnframes() == 0:
            return False
        while chunk := audio.readframes(65536):
            if any(chunk):
                return False
    return True


def ffmpeg_tools(environment_root: Path) -> tuple[Path, Path]:
    bundled = list((environment_root / "tools" / "ffmpeg").glob("*/bin/ffmpeg.exe"))
    executable = bundled[0] if bundled else shutil.which("ffmpeg")
    if not executable:
        raise RuntimeError("FFmpeg is missing. Configure the project environment first.")
    ffmpeg = Path(executable)
    probe = ffmpeg.with_name("ffprobe" + ffmpeg.suffix)
    if not probe.is_file():
        raise RuntimeError("ffprobe is missing beside ffmpeg.")
    os.environ["PATH"] = str(ffmpeg.parent) + os.pathsep + os.environ["PATH"]
    return ffmpeg, probe


def probe_media(source: Path, ffprobe: Path) -> dict:
    if not source.is_file():
        raise ValueError(f"Input file does not exist: {source}")
    result = subprocess.run(
        [
            str(ffprobe),
            "-v",
            "error",
            "-protocol_whitelist",
            "file,pipe",
            "-show_format",
            "-show_streams",
            "-of",
            "json",
            str(source.resolve()),
        ],
        capture_output=True,
        text=True,
        timeout=60,
    )
    if result.returncode:
        raise MediaInputError("Input cannot be decoded as a supported audio/video recording.")
    info = json.loads(result.stdout)
    audio = next(
        (stream for stream in info.get("streams", []) if stream.get("codec_type") == "audio"), None
    )
    if audio is None:
        raise MediaInputError("The input has no audio stream.")
    duration = float(audio.get("duration") or info.get("format", {}).get("duration", 0))
    if not 0 < duration < float("inf"):
        raise MediaInputError("Recording duration is unavailable or invalid.")
    return {"duration": duration, "audio_stream_index": audio["index"]}


def decode(
    source: Path,
    destination: Path,
    ffmpeg: Path,
    audio_index: int,
    start: float = 0,
    duration: float | None = None,
) -> float:
    command = [
        str(ffmpeg),
        "-nostdin",
        "-v",
        "error",
        "-protocol_whitelist",
        "file,pipe",
        "-i",
        str(source.resolve()),
        "-ss",
        str(start),
    ]
    if duration is not None:
        command += ["-t", str(duration)]
    command += [
        "-map",
        f"0:{audio_index}",
        "-vn",
        "-ac",
        "1",
        "-ar",
        "16000",
        "-c:a",
        "pcm_s16le",
        "-y",
        str(destination),
    ]
    result = subprocess.run(command, capture_output=True, text=True, timeout=600)
    if result.returncode:
        raise ValueError("FFmpeg could not extract the audio track.")
    with wave.open(str(destination)) as audio:
        actual_duration = audio.getnframes() / audio.getframerate()
    if actual_duration <= 0:
        raise MediaInputError("The selected audio interval is empty.")
    return actual_duration
