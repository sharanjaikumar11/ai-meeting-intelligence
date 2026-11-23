"""Verify installed dependencies without credentials or model downloads."""

import argparse
import importlib
import importlib.metadata as metadata
import json
import os
import subprocess
import tempfile
from pathlib import Path


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--environment-root", type=Path, required=True)
    args = parser.parse_args()
    ROOT = args.environment_root.resolve()
    ffmpeg = next((ROOT / "tools" / "ffmpeg").glob("*/bin/ffmpeg.exe"))
    os.environ["PATH"] = str(ffmpeg.parent) + os.pathsep + os.environ["PATH"]
    dll_handle = os.add_dll_directory(str(ffmpeg.parent))
    packages = {
        "openai-whisper": "whisper",
        "pyannote.audio": "pyannote.audio",
        "torch": "torch",
        "torchaudio": "torchaudio",
        "torchcodec": "torchcodec",
        "google-genai": "google.genai",
        "fastapi": "fastapi",
        "uvicorn": "uvicorn",
        "python-multipart": "python_multipart",
        "pydantic": "pydantic",
        "python-dotenv": "dotenv",
        "jiwer": "jiwer",
        "scikit-learn": "sklearn",
        "soundfile": "soundfile",
        "pytest": "pytest",
        "httpx": "httpx",
    }
    versions = {}
    for distribution, module in packages.items():
        importlib.import_module(module)
        versions[distribution] = metadata.version(distribution)
        print(f"PASS import {distribution} {versions[distribution]}", flush=True)

    import torch
    import whisper
    from fastapi import FastAPI
    from fastapi.testclient import TestClient
    from jiwer import wer
    from sklearn.metrics import precision_recall_fscore_support
    from torchcodec.decoders import AudioDecoder

    with tempfile.TemporaryDirectory(dir=ROOT) as directory:
        wav = Path(directory) / "smoke.wav"
        subprocess.run(
            [
                str(ffmpeg),
                "-v",
                "error",
                "-f",
                "lavfi",
                "-i",
                "sine=frequency=440:duration=1",
                "-ar",
                "16000",
                "-ac",
                "1",
                str(wav),
            ],
            check=True,
        )
        samples = whisper.load_audio(str(wav))
        assert len(samples) == 16000
        mel = whisper.log_mel_spectrogram(samples)
        assert mel.shape[0] == 80
        decoded = AudioDecoder(str(wav)).get_all_samples()
        assert decoded.sample_rate == 16000
        assert decoded.data.shape[-1] == 16000
        print("PASS FFmpeg, Whisper preprocessing, TorchCodec audio decoding")

    app = FastAPI()

    @app.get("/health")
    def health():
        return {"status": "ok"}

    assert TestClient(app).get("/health").json() == {"status": "ok"}
    assert wer("meeting deadline Monday", "meeting deadline Monday") == 0
    assert precision_recall_fscore_support([1, 0], [1, 0], average="binary")[2] == 1
    print("PASS FastAPI request and evaluation metrics")
    report = {
        "status": "passed",
        "versions": versions,
        "cuda_available": torch.cuda.is_available(),
        "checks": [
            "imports",
            "ffmpeg",
            "whisper preprocessing",
            "torchcodec decoding",
            "fastapi request",
            "metrics",
        ],
        "not_tested": [
            "downloaded Whisper model inference",
            "gated diarization model inference",
            "Gemini API request",
        ],
    }
    (ROOT / "environment-validation.json").write_text(json.dumps(report, indent=2))
    print(json.dumps(report, indent=2))
    dll_handle.close()


if __name__ == "__main__":
    main()
