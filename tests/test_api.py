import pytest
from fastapi.testclient import TestClient
from app.main import app

client = TestClient(app)


def test_health_check():
    response = client.get("/health")
    assert response.status_code == 200
    assert response.json() == {"status": "ok"}


def test_root():
    response = client.get("/")
    assert response.status_code == 200
    assert response.json()["service"] == "Mock Interview AI"


def test_create_session_missing_fields():
    response = client.post("/api/v1/sessions", json={})
    assert response.status_code == 422


def test_get_session_not_found():
    response = client.get("/api/v1/sessions/99999")
    assert response.status_code == 404
    assert response.json()["detail"] == "Session not found"