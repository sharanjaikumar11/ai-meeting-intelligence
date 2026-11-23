"""Compare Whisper models on fixed development clips; retain all predictions."""

import argparse
import gc
import importlib.metadata
import json
import os
import platform
import time
from datetime import datetime, timezone
from pathlib import Path


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--environment-root", type=Path, required=True)
    parser.add_argument("--models", nargs="+", default=["tiny", "base"])
    parser.add_argument("--threads", type=int, default=4)
    args = parser.parse_args()
    root = args.environment_root
    ffmpeg = next((root / "tools" / "ffmpeg").glob("*/bin/ffmpeg.exe"))
    os.environ["PATH"] = str(ffmpeg.parent) + os.pathsep + os.environ["PATH"]
    import jiwer
    import torch
    import whisper
    from whisper.normalizers import EnglishTextNormalizer

    torch.set_num_threads(args.threads)
    torch.manual_seed(0)
    normalize = EnglishTextNormalizer()
    benchmark = json.loads((root / "data" / "benchmark_windows.json").read_text(encoding="utf-8"))
    output = root / "outputs" / "day01"
    output.mkdir(parents=True, exist_ok=True)
    report = {
        "created_utc": datetime.now(timezone.utc).isoformat(),
        "python": platform.python_version(),
        "whisper_version": importlib.metadata.version("openai-whisper"),
        "torch_version": torch.__version__,
        "device": "cpu",
        "threads": args.threads,
        "benchmark_version": benchmark.get("version", 1),
        "normalization": "Whisper EnglishTextNormalizer applied to both reference and hypothesis",
        "decoding": {
            "language": "en",
            "task": "transcribe",
            "fp16": False,
            "temperature": 0,
            "condition_on_previous_text": False,
        },
        "limitations": [
            "Three development clips from one headset-mix meeting.",
            "Overlap serialized by onset; boundary words selected by midpoint.",
            "No claim of final evaluation accuracy or speaker diarization quality.",
            "Timing includes per-clip preprocessing; model loading measured separately.",
        ],
        "results": [],
    }
    for name in args.models:
        print(f"Loading {name}", flush=True)
        started = time.perf_counter()
        model = whisper.load_model(
            name, device="cpu", download_root=str(root / "models" / "whisper")
        )
        load_seconds = time.perf_counter() - started
        clips = []
        for clip in benchmark["windows"]:
            print(f"Transcribing {name}: {clip['clip_id']}", flush=True)
            started = time.perf_counter()
            prediction = model.transcribe(clip["audio_path"], verbose=None, **report["decoding"])
            elapsed = time.perf_counter() - started
            ref, hyp = normalize(clip["reference_text"]), normalize(prediction["text"])
            metrics = jiwer.process_words(ref, hyp)
            segments = [
                {
                    "start": segment["start"] + clip["start"],
                    "end": segment["end"] + clip["start"],
                    "text": segment["text"],
                }
                for segment in prediction["segments"]
            ]
            result = {
                "clip_id": clip["clip_id"],
                "start": clip["start"],
                "end": clip["end"],
                "reference": clip["reference_text"],
                "prediction": prediction["text"],
                "normalized_reference": ref,
                "normalized_prediction": hyp,
                "seconds": elapsed,
                "wer": metrics.wer,
                "substitutions": metrics.substitutions,
                "deletions": metrics.deletions,
                "insertions": metrics.insertions,
                "reference_words": metrics.hits + metrics.substitutions + metrics.deletions,
                "segments": segments,
            }
            clips.append(result)
            (output / f"{name}_{clip['clip_id']}.json").write_text(
                json.dumps(result, indent=2), encoding="utf-8"
            )
            print(
                f"WER {metrics.wer:.3%}; {elapsed:.1f}s for {clip['end'] - clip['start']}s audio",
                flush=True,
            )
        words = sum(clip["reference_words"] for clip in clips)
        errors = sum(
            clip["substitutions"] + clip["deletions"] + clip["insertions"] for clip in clips
        )
        total_seconds = sum(clip["seconds"] for clip in clips)
        total_audio = sum(clip["end"] - clip["start"] for clip in clips)
        report["results"].append(
            {
                "model": name,
                "load_seconds": load_seconds,
                "wer": errors / words,
                "reference_words": words,
                "word_errors": errors,
                "inference_seconds": total_seconds,
                "audio_seconds": total_audio,
                "real_time_factor": total_seconds / total_audio,
                "clips": clips,
            }
        )
        (output / f"benchmark_{'_'.join(args.models)}.json").write_text(
            json.dumps(report, indent=2), encoding="utf-8"
        )
        del model
        gc.collect()
    print(
        json.dumps(
            [
                {key: value for key, value in result.items() if key != "clips"}
                for result in report["results"]
            ],
            indent=2,
        )
    )


if __name__ == "__main__":
    main()
