from __future__ import annotations

import importlib
import json
import sys
from pathlib import Path

from fastapi.testclient import TestClient


def _load_main(monkeypatch, fingerprint_path: Path):
    monkeypatch.setenv("OPENAI_API_KEY", "dummy")
    monkeypatch.setenv("DATABASE_URL", "sqlite://")
    monkeypatch.setenv("DEPLOY_FINGERPRINT_PATH", str(fingerprint_path))
    if "main" in sys.modules:
        del sys.modules["main"]
    import main  # type: ignore

    return importlib.reload(main)


def test_health_deploy_returns_version_without_fingerprint(monkeypatch, tmp_path) -> None:
    main = _load_main(monkeypatch, tmp_path / "missing.json")

    response = TestClient(main.app).get("/health/deploy")

    assert response.status_code == 200
    assert response.json()["status"] == "ok"
    assert response.json()["version"] == "0.3.1"


def test_health_deploy_includes_fingerprint(monkeypatch, tmp_path) -> None:
    fingerprint_path = tmp_path / "fingerprint.json"
    fingerprint_path.write_text(
        json.dumps(
            {
                "environment": "vps-prod",
                "git_sha": "abc123",
                "git_branch": "HEAD",
                "git_tag": "",
                "deployed_at_utc": "2026-04-24T00:00:00Z",
                "deployed_by": "deploy@example",
                "source": "deploy.sh",
                "image": "esg-api:test",
            }
        ),
        encoding="utf-8",
    )
    main = _load_main(monkeypatch, fingerprint_path)

    payload = TestClient(main.app).get("/health/deploy").json()

    assert payload["version"] == "0.3.1"
    assert payload["environment"] == "vps-prod"
    assert payload["git_sha"] == "abc123"
    assert payload["source"] == "deploy.sh"


def test_health_deploy_survives_bad_fingerprint(monkeypatch, tmp_path) -> None:
    fingerprint_path = tmp_path / "fingerprint.json"
    fingerprint_path.mkdir()
    main = _load_main(monkeypatch, fingerprint_path)

    payload = TestClient(main.app).get("/health/deploy").json()

    assert payload["status"] == "ok"
    assert payload["version"] == "0.3.1"
    assert payload["fingerprint_error"]


def test_health_deploy_rejects_non_object_fingerprint(monkeypatch, tmp_path) -> None:
    fingerprint_path = tmp_path / "fingerprint.json"
    fingerprint_path.write_text("[]", encoding="utf-8")
    main = _load_main(monkeypatch, fingerprint_path)

    payload = TestClient(main.app).get("/health/deploy").json()

    assert payload["status"] == "ok"
    assert payload["version"] == "0.3.1"
    assert "JSON object" in payload["fingerprint_error"]


def test_health_deploy_does_not_allow_fingerprint_to_override_status(monkeypatch, tmp_path) -> None:
    fingerprint_path = tmp_path / "fingerprint.json"
    fingerprint_path.write_text(
        json.dumps({"status": "bad", "version": "0.0.0", "git_sha": "abc123"}),
        encoding="utf-8",
    )
    main = _load_main(monkeypatch, fingerprint_path)

    payload = TestClient(main.app).get("/health/deploy").json()

    assert payload["status"] == "ok"
    assert payload["version"] == "0.3.1"
    assert payload["git_sha"] == "abc123"
