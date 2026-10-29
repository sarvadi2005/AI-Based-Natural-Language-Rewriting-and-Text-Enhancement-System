from __future__ import annotations

import pytest
from fastapi.testclient import TestClient

from app.main import app


@pytest.fixture()
def client(tmp_path, monkeypatch):
    monkeypatch.setenv("TEXT_REWRITER_DB_PATH", str(tmp_path / "test.sqlite3"))
    with TestClient(app) as test_client:
        yield test_client


def test_root_and_health_identify_local_rule_engine(client):
    root = client.get("/")
    health = client.get("/health")

    assert root.status_code == 200
    assert root.json()["engine"] == "deterministic_rule_based"
    assert "rule-based" in root.json()["engine_description"]
    assert health.status_code == 200
    assert health.json()["status"] == "ok"


@pytest.mark.parametrize(
    ("mode", "canonical_mode"),
    [
        ("paraphrase", "paraphrase"),
        ("academic", "academic"),
        ("professional", "professional"),
        ("simple", "simple"),
        ("friendly", "friendly"),
        ("concise", "concise"),
        ("expand", "expand"),
        ("grammar", "grammar"),
        ("improve", "paraphrase"),
        ("simplify", "simple"),
        ("creative", "expand"),
        ("persuasive", "professional"),
    ],
)
def test_rewrite_supports_canonical_and_legacy_modes(client, mode, canonical_mode):
    response = client.post(
        "/api/rewrite",
        json={"text": "This is a very important thing and it is a lot of work.", "mode": mode},
    )

    assert response.status_code == 200
    body = response.json()
    assert body["mode"] == mode
    assert body["canonical_mode"] == canonical_mode
    assert body["enhanced_text"] == body["rewritten_text"]
    assert body["enhanced_text"].strip()
    assert body["status"] == "success"
    assert body["engine"] == "deterministic_rule_based"
    assert isinstance(body["changes"], list)
    assert 0 <= body["quality_score"] <= 100


def test_rewrite_accepts_frontend_request_and_response_contract(client):
    response = client.post(
        "/api/rewrite",
        json={"text": "We can't use this because of the fact that it is bad.", "mode": "improve"},
    )

    assert response.status_code == 200
    body = response.json()
    assert body["original_text"].startswith("We can't")
    assert body["enhanced_text"] == body["rewritten_text"]
    assert body["word_count_before"] > 0
    assert body["word_count_after"] > 0
    assert body["processing_time"] >= 0
    assert body["mode"] == "improve"
    assert body["canonical_mode"] == "paraphrase"


def test_rewrite_validation_rejects_blank_and_unknown_modes(client):
    blank = client.post("/api/rewrite", json={"text": "  ", "mode": "grammar"})
    unknown_mode = client.post("/api/rewrite", json={"text": "Some text.", "mode": "creative-writing"})
    missing_text = client.post("/api/rewrite", json={"mode": "paraphrase"})

    assert blank.status_code == 422
    assert unknown_mode.status_code == 422
    assert missing_text.status_code == 422


def test_evaluate_returns_metrics_for_frontend(client):
    response = client.post(
        "/api/evaluate",
        json={
            "original_text": "The project is good.",
            "rewritten_text": "The project is beneficial.",
        },
    )

    assert response.status_code == 200
    body = response.json()
    assert body["rewritten_text"] == "The project is beneficial."
    assert body["word_count"] == 4
    assert body["sentence_count"] == 1
    assert body["average_sentence_length"] == 4
    assert 0 <= body["quality_score"] <= 100
    assert "quality_score" in body["metrics"]
    assert "quality_score_change" in body["metrics"]
    assert "does not measure factual" in body["quality_score_basis"]


def test_evaluate_reports_missing_readability_for_non_english_text(client):
    response = client.post(
        "/api/evaluate",
        json={"original_text": "你好世界。", "rewritten_text": "你好，世界。"},
    )

    assert response.status_code == 200
    assert response.json()["readability"] is None


def test_history_persists_lists_retrieves_and_deletes_records(client):
    created = client.post(
        "/api/rewrite",
        json={"text": "This is a very important thing.", "mode": "professional"},
    ).json()

    listed = client.get("/api/history")
    assert listed.status_code == 200
    assert isinstance(listed.json(), list)
    assert len(listed.json()) == 1
    saved = listed.json()[0]
    assert saved["original_text"] == created["original_text"]
    assert saved["enhanced_text"] == created["enhanced_text"]
    assert saved["mode"] == "professional"
    assert saved["created_at"]
    assert "quality_score" in saved["metrics"]

    retrieved = client.get(f"/api/history/{saved['id']}")
    assert retrieved.status_code == 200
    assert retrieved.json()["id"] == saved["id"]
    assert client.get("/api/history/999999").status_code == 404

    deleted = client.delete("/api/history")
    assert deleted.status_code == 200
    assert deleted.json() == {"deleted_count": 1, "status": "success"}
    assert client.get("/api/history").json() == []


def test_cors_allows_both_frontend_origins(client):
    for origin in ("http://127.0.0.1:5500", "http://localhost:5500"):
        response = client.options(
            "/api/rewrite",
            headers={
                "Origin": origin,
                "Access-Control-Request-Method": "POST",
                "Access-Control-Request-Headers": "content-type",
            },
        )
        assert response.status_code == 200
        assert response.headers["access-control-allow-origin"] == origin


def test_history_limit_is_validated(client):
    assert client.get("/api/history?limit=0").status_code == 422
    assert client.get("/api/history?limit=501").status_code == 422
