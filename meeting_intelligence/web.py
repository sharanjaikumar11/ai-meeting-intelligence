"""Local Day 7 web application. Run with python -m meeting_intelligence.web."""

import argparse
import json
import threading
from concurrent.futures import ThreadPoolExecutor
from datetime import date
from pathlib import Path
from uuid import uuid4

from fastapi import FastAPI, File, Form, HTTPException, Request, UploadFile
from fastapi.responses import FileResponse
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel, ConfigDict, Field
from starlette.middleware.trustedhost import TrustedHostMiddleware

from .action_extraction import ACTION_INSTRUCTION, extract_actions
from .action_schemas import GeneratedActions
from .decision_tracking import (
    INSTRUCTION,
    DecisionReviewGenerator,
    GeneratedDecisions,
    track_decisions,
)
from .media import MediaInputError
from .pipeline import transcribe
from .qa import INSTRUCTION as QA_INSTRUCTION
from .qa import GeneratedAnswer, QAReviewGenerator, ask
from .schemas import Transcript
from .summarization import GeminiGenerator, SummaryError, settings_from_environment, summarize


class Question(BaseModel):
    model_config = ConfigDict(str_strip_whitespace=True)
    question: str = Field(min_length=1, max_length=2000)


def create_app(environment_root: Path, worker=None):
    app = FastAPI(title="Meeting Intelligence")
    app.add_middleware(
        TrustedHostMiddleware, allowed_hosts=["127.0.0.1", "localhost", "testserver"]
    )
    root = environment_root / "outputs/web"
    root.mkdir(parents=True, exist_ok=True)
    pool = ThreadPoolExecutor(max_workers=1)
    lock = threading.RLock()
    busy = set()
    static = Path(__file__).parent / "static"
    app.mount("/static", StaticFiles(directory=static), name="static")

    @app.middleware("http")
    async def same_origin(request: Request, call_next):
        origin = request.headers.get("origin")
        if (
            request.method not in {"GET", "HEAD", "OPTIONS"}
            and origin
            and origin != str(request.base_url).rstrip("/")
        ):
            from fastapi.responses import JSONResponse

            return JSONResponse(
                {"detail": "Cross-origin requests are not permitted."}, status_code=403
            )
        return await call_next(request)

    def folder(job_id):
        if len(job_id) != 32 or any(c not in "0123456789abcdef" for c in job_id):
            raise HTTPException(404, "Meeting not found")
        path = root / job_id
        if not (path / "state.json").exists():
            raise HTTPException(404, "Meeting not found")
        return path

    def save(path, name, value):
        with lock:
            temporary = path / (name + ".tmp")
            temporary.write_text(json.dumps(value, indent=2), encoding="utf-8")
            temporary.replace(path / name)

    def read(path):
        with lock:
            return json.loads(path.read_text(encoding="utf-8"))

    def pipeline(path, state):
        def stage(name):
            state.update(status="processing", stage=name, error=None)
            save(path, "state.json", state)

        try:
            result = read(path / "result.json") if (path / "result.json").exists() else {}
            if worker:
                result = worker(path, state)
                save(path, "result.json", result)
            else:
                if "transcript" not in result:
                    stage("Transcribing and identifying speakers")
                    t = transcribe(
                        path / "recording",
                        environment_root,
                        start=state["start"],
                        duration=state["duration"],
                        skip_diarization=not state["diarize"],
                        diarization_context=300,
                    )
                    result["transcript"] = t.model_dump(mode="json")
                    save(path, "result.json", result)
                t = Transcript.model_validate(result["transcript"])
                settings = settings_from_environment(environment_root)
                meeting_date = (
                    date.fromisoformat(state["meeting_date"]) if state["meeting_date"] else None
                )
                for name, label, fn in [
                    (
                        "summary",
                        "Summarizing",
                        lambda: summarize(t, settings.model, GeminiGenerator(settings)),
                    ),
                    (
                        "actions",
                        "Extracting tasks and deadlines",
                        lambda: extract_actions(
                            t,
                            settings.model,
                            GeminiGenerator(
                                settings, schema=GeneratedActions, instruction=ACTION_INSTRUCTION
                            ),
                            meeting_date,
                        ),
                    ),
                    (
                        "decisions",
                        "Tracking decision changes",
                        lambda: track_decisions(
                            t,
                            settings.model,
                            DecisionReviewGenerator(
                                GeminiGenerator(
                                    settings,
                                    schema=GeneratedDecisions,
                                    instruction=INSTRUCTION,
                                    max_output_tokens=16384,
                                )
                            ),
                            meeting_date,
                        ),
                    ),
                ]:
                    if name not in result:
                        stage(label)
                        result[name] = fn().model_dump(mode="json")
                        save(path, "result.json", result)
            state.update(status="completed", stage="Ready", error=None)
        except Exception as exc:
            state.update(
                status="failed",
                error=str(exc)
                if isinstance(exc, (SummaryError, MediaInputError))
                else "Processing failed. Check the recording and local model setup; completed stages are preserved.",
            )
        finally:
            with lock:
                try:
                    save(path, "state.json", state)
                finally:
                    busy.discard(state["id"])

    def launch(path, state):
        with lock:
            if busy:
                raise HTTPException(409, "Another meeting is processing. Please wait.")
            busy.add(state["id"])
        state.update(status="queued", error=None)
        save(path, "state.json", state)
        pool.submit(pipeline, path, state)

    @app.get("/")
    def index():
        return FileResponse(static / "index.html")

    @app.get("/api/meetings")
    def meetings():
        items = []
        for p in root.glob("*/state.json"):
            state = read(p)
            if state["status"] in {"queued", "processing"} and state["id"] not in busy:
                state.update(
                    status="interrupted", error="Server restarted. Retry to continue saved stages."
                )
            items.append(state)
        return items[::-1]

    @app.post("/api/meetings", status_code=202)
    async def upload(
        recording: UploadFile = File(...),
        diarize: bool = Form(True),
        start: float = Form(0, ge=0, allow_inf_nan=False),
        duration: float | None = Form(None, gt=0, allow_inf_nan=False),
        meeting_date: date | None = Form(None),
    ):
        with lock:
            if busy:
                raise HTTPException(409, "Another meeting is processing.")
        job_id = uuid4().hex
        path = root / job_id
        path.mkdir()
        size = 0
        try:
            with (path / "recording").open("wb") as out:
                while chunk := await recording.read(1024 * 1024):
                    size += len(chunk)
                    if size > 500 * 1024 * 1024:
                        raise HTTPException(413, "Maximum upload size is 500 MB.")
                    out.write(chunk)
            if not size:
                raise HTTPException(400, "Recording is empty.")
            state = dict(
                id=job_id,
                name=Path(recording.filename or "Meeting").name,
                status="queued",
                stage="Queued",
                error=None,
                start=start,
                duration=duration,
                diarize=diarize,
                meeting_date=meeting_date.isoformat() if meeting_date else None,
            )
            launch(path, state)
            return state
        except Exception:
            if not (path / "state.json").exists():
                (path / "recording").unlink(missing_ok=True)
                path.rmdir()
            raise
        finally:
            await recording.close()

    @app.get("/api/meetings/{job_id}")
    def get_meeting(job_id: str):
        path = folder(job_id)
        state = read(path / "state.json")
        if state["status"] in {"queued", "processing"} and job_id not in busy:
            state["status"] = "interrupted"
        state["result"] = read(path / "result.json") if (path / "result.json").exists() else {}
        return state

    @app.post("/api/meetings/{job_id}/retry", status_code=202)
    def retry(job_id: str):
        path = folder(job_id)
        state = read(path / "state.json")
        if state["status"] == "completed":
            raise HTTPException(409, "Meeting already completed.")
        launch(path, state)
        return {"status": "queued"}

    @app.get("/api/meetings/{job_id}/download")
    def download(job_id: str):
        path = folder(job_id) / "result.json"
        if not path.exists():
            raise HTTPException(409, "No results yet.")
        return FileResponse(path, media_type="application/json", filename="meeting.json")

    @app.post("/api/meetings/{job_id}/questions")
    def question(job_id: str, body: Question):
        data = get_meeting(job_id)["result"]
        if "transcript" not in data:
            raise HTTPException(409, "Transcript is not ready.")
        try:
            settings = settings_from_environment(environment_root)
            generator = QAReviewGenerator(
                GeminiGenerator(settings, schema=GeneratedAnswer, instruction=QA_INSTRUCTION)
            )
            return ask(
                Transcript.model_validate(data["transcript"]),
                body.question,
                settings.model,
                generator,
            )
        except (ValueError, RuntimeError) as exc:
            raise HTTPException(
                503, str(exc) if isinstance(exc, SummaryError) else "Question answering failed."
            ) from None

    return app


if __name__ == "__main__":
    import uvicorn

    p = argparse.ArgumentParser()
    p.add_argument("--environment-root", type=Path, required=True)
    p.add_argument("--port", type=int, default=8000)
    args = p.parse_args()
    uvicorn.run(create_app(args.environment_root), host="127.0.0.1", port=args.port)
