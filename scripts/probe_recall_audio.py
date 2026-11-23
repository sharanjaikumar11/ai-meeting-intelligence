"""Development-only audio recheck; no reference hints are supplied to Whisper."""

import argparse
import hashlib
import json
import sys
import tempfile
import time
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from meeting_intelligence.media import decode, ffmpeg_tools, probe_media


def main():
    p = argparse.ArgumentParser()
    p.add_argument("--environment-root", type=Path, required=True)
    a = p.parse_args()
    root = a.environment_root
    out = root / "outputs/day10/recall_audio_probe"
    out.mkdir(parents=True, exist_ok=True)
    source = root / "data/recordings/IS1003b.Mix-Headset.wav"
    start, duration = 1555, 30
    import jiwer
    import torch
    import whisper
    from whisper.normalizers import EnglishTextNormalizer

    torch.set_num_threads(4)
    torch.manual_seed(0)
    normalize = EnglishTextNormalizer()
    ffmpeg, ffprobe = ffmpeg_tools(root)
    info = probe_media(source, ffprobe)
    report = {
        "scope": "Known missed-task diagnostic, not held-out evaluation; no end-to-end recall claim",
        "source": str(source),
        "start": start,
        "duration": duration,
        "model": "small",
        "threads": 4,
        "reference_hints_supplied_to_model": False,
        "gemini_requests": 0,
        "script_sha256": hashlib.sha256(Path(__file__).read_bytes()).hexdigest(),
        "results": [],
    }
    with tempfile.TemporaryDirectory() as folder:
        wav = Path(folder) / "probe.wav"
        decode(source, wav, ffmpeg, info["audio_stream_index"], start, duration)
        model = whisper.load_model(
            "small", device="cpu", download_root=str(root / "models/whisper")
        )
        for name, beam in [("greedy", None), ("beam5", 5)]:
            dest = out / f"{name}.json"
            if not dest.exists():
                print("Local audio recheck:", name, flush=True)
                began = time.perf_counter()
                options = dict(
                    language="en",
                    task="transcribe",
                    fp16=False,
                    word_timestamps=True,
                    temperature=0,
                    condition_on_previous_text=False,
                    verbose=None,
                )
                if beam:
                    options["beam_size"] = beam
                result = model.transcribe(str(wav), **options)
                dest.write_text(
                    json.dumps(
                        dict(
                            text=result["text"],
                            segments=result["segments"],
                            seconds=time.perf_counter() - began,
                        ),
                        indent=2,
                    ),
                    encoding="utf-8",
                )
            prediction = json.loads(dest.read_text())
            # Human text is read only for scoring, after inference, never as a decoding prompt.
            reference = json.loads(
                (root / "outputs/day09/IS1003b_1458_1614.reference.json").read_text()
            )
            words = [
                w
                for w in reference["words"]
                if start <= (w["start"] + w["end"]) / 2 < start + duration
            ]
            r = normalize(" ".join(w["text"] for w in words))
            h = normalize(prediction["text"])
            m = jiwer.process_words(r, h)
            report["results"].append(
                dict(
                    decoding=name,
                    prediction=prediction["text"],
                    reference=r,
                    wer=m.wer,
                    substitutions=m.substitutions,
                    deletions=m.deletions,
                    insertions=m.insertions,
                    reference_words=m.hits + m.substitutions + m.deletions,
                    seconds=prediction["seconds"],
                )
            )
            (out / "report.json").write_text(json.dumps(report, indent=2), encoding="utf-8")
            print(name, prediction["text"], "WER", m.wer, flush=True)
    original = json.loads((root / "outputs/day09/IS1003b_1458_1614.transcript.json").read_text())
    selected = [
        w
        for s in original["segments"]
        for w in s["words"]
        if start <= (w["start"] + w["end"]) / 2 < start + duration
    ]
    original_text = " ".join(w["text"] for w in selected)
    m = jiwer.process_words(r, normalize(original_text))
    report["original_window"] = dict(
        prediction=original_text,
        wer=m.wer,
        substitutions=m.substitutions,
        deletions=m.deletions,
        insertions=m.insertions,
        reference_words=m.hits + m.substitutions + m.deletions,
        boundary_policy="Original hypothesis words selected by midpoint; new probes transcribe the exact audio crop. Alignment differences can affect boundary words.",
    )
    (out / "report.json").write_text(json.dumps(report, indent=2), encoding="utf-8")


if __name__ == "__main__":
    main()
