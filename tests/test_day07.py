import time

from fastapi.testclient import TestClient

from meeting_intelligence.web import create_app


def client(tmp_path, worker=None):
    return TestClient(
        create_app(tmp_path, worker or (lambda p, s: {"transcript": {"segments": []}}))
    )


def wait(c, id):
    for _ in range(500):
        r = c.get("/api/meetings/" + id).json()
        if r["status"] in {"completed", "failed"}:
            return r
        time.sleep(0.01)
    raise AssertionError("Job did not finish")


def test_upload_status_download_and_persistence(tmp_path):
    c = client(tmp_path)
    r = c.post(
        "/api/meetings",
        files={"recording": ("meeting.wav", b"test-only-mocked-audio")},
        data={"diarize": "false"},
    )
    assert r.status_code == 202
    id = r.json()["id"]
    assert wait(c, id)["status"] == "completed"
    assert c.get(f"/api/meetings/{id}/download").json()["transcript"] == {"segments": []}
    assert client(tmp_path).get("/api/meetings").json()[0]["id"] == id
    assert c.post(f"/api/meetings/{id}/retry").status_code == 409


def test_failure_then_retry(tmp_path):
    calls = []

    def worker(p, s):
        calls.append(s["id"])
        if len(calls) == 1:
            raise RuntimeError("private internal error")
        return {"transcript": {"segments": []}}

    c = client(tmp_path, worker)
    id = c.post("/api/meetings", files={"recording": ("x.wav", b"x")}).json()["id"]
    failed = wait(c, id)
    assert failed["status"] == "failed" and "private" not in failed["error"]
    assert c.post(f"/api/meetings/{id}/retry").status_code == 202
    assert wait(c, id)["status"] == "completed"


def test_validation_and_origin(tmp_path):
    c = client(tmp_path)
    assert c.post("/api/meetings", files={"recording": ("x.wav", b"")}).status_code == 400
    assert (
        c.post(
            "/api/meetings", files={"recording": ("x.wav", b"x")}, data={"duration": "-1"}
        ).status_code
        == 422
    )
    assert (
        c.post(
            "/api/meetings",
            headers={"Origin": "https://untrusted.example"},
            files={"recording": ("x.wav", b"x")},
        ).status_code
        == 403
    )
    assert c.get("/api/meetings/not-an-id").status_code == 404
    assert c.get("/", headers={"Host": "untrusted.example"}).status_code == 400


def test_ui_assets(tmp_path):
    c = client(tmp_path)
    assert c.get("/").status_code == 200
    assert "Ask the meeting" in c.get("/").text
    assert "textContent" in c.get("/static/app.js").text
    assert c.get("/static/style.css").status_code == 200


def test_pipeline_wires_all_stages_and_keeps_partial_results(tmp_path, monkeypatch):
    from types import SimpleNamespace

    from test_day03 import transcript

    from meeting_intelligence import web
    from meeting_intelligence.summarization import SummaryError

    calls = []

    def transcribe(*a, **k):
        calls.append("transcript")
        return transcript()

    def stage(name):
        def f(*a, **k):
            calls.append(name)
            return SimpleNamespace(model_dump=lambda **k: {"stage": name})

        return f

    monkeypatch.setattr(web, "transcribe", transcribe)
    monkeypatch.setattr(
        web, "settings_from_environment", lambda root: SimpleNamespace(model="test", api_key="test")
    )
    monkeypatch.setattr(web, "summarize", stage("summary"))
    monkeypatch.setattr(
        web,
        "extract_actions",
        lambda *a, **k: (_ for _ in ()).throw(SummaryError("Gemini daily quota reached.")),
    )
    monkeypatch.setattr(web, "track_decisions", stage("decisions"))
    c = TestClient(create_app(tmp_path))
    id = c.post("/api/meetings", files={"recording": ("x.wav", b"mocked")}).json()["id"]
    result = wait(c, id)
    assert result["status"] == "failed" and set(result["result"]) == {"transcript", "summary"}
    monkeypatch.setattr(web, "extract_actions", stage("actions"))
    c.post(f"/api/meetings/{id}/retry")
    result = wait(c, id)
    assert result["status"] == "completed" and set(result["result"]) == {
        "transcript",
        "summary",
        "actions",
        "decisions",
    }
    assert calls == ["transcript", "summary", "actions", "decisions"]
