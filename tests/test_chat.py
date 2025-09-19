import pytest
from fastapi import FastAPI
from fastapi.testclient import TestClient

# Import the router under test
from backend.routes import chat as chat_router


@pytest.fixture(scope="module")
def app() -> FastAPI:
    app = FastAPI()
    app.include_router(chat_router.router)
    return app


@pytest.fixture(scope="module")
def client(app) -> TestClient:
    return TestClient(app)


def test_chat_success(monkeypatch, client: TestClient):
    """Happy path: ensure the route returns mocked response & history."""

    def fake_generate_response(query, history):
        assert query == "find red shoes"
        assert history == ["User: hi"]
        return "Here are red shoes.", ["User: hi", "Assistant: Here are red shoes."]

    # IMPORTANT: patch where it's USED, not where it's defined
    monkeypatch.setattr(
        "backend.routes.chat.generate_response",
        fake_generate_response,
        raising=True,
    )

    payload = {"query": "find red shoes", "history": ["User: hi"]}
    resp = client.post("/chat", json=payload)

    assert resp.status_code == 200
    data = resp.json()
    assert data["response"] == "Here are red shoes."
    assert data["history"] == ["User: hi", "Assistant: Here are red shoes."]


def test_chat_uses_default_history(monkeypatch, client: TestClient):
    """If history omitted, the route should pass [] to the chain."""

    def fake_generate_response(query, history):
        assert query == "hello"
        assert history == []  # default from the Pydantic model
        return "Hi there!", ["Assistant: Hi there!"]

    monkeypatch.setattr(
        "backend.routes.chat.generate_response",
        fake_generate_response,
        raising=True,
    )

    resp = client.post("/chat", json={"query": "hello"})
    assert resp.status_code == 200
    data = resp.json()
    assert data["response"] == "Hi there!"
    assert data["history"] == ["Assistant: Hi there!"]


def test_chat_validation_error_missing_query(client: TestClient):
    """FastAPI should 422 when required field is missing."""
    resp = client.post("/chat", json={"history": []})
    assert resp.status_code == 422
    body = resp.json()
    # minimal check that 'query' is reported missing by the validator
    assert body["detail"][0]["loc"][-1] == "query"
