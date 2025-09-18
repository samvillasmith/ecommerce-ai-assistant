# tests/test_providers_embeddings.py
import importlib
import os
import sys
from types import SimpleNamespace
import pytest

MODPATH = "providers.embeddings"


def fresh_import():
    """Re-import the module cleanly after we prepare env and fake deps."""
    if MODPATH in sys.modules:
        del sys.modules[MODPATH]
    return importlib.import_module(MODPATH)


@pytest.fixture(autouse=True)
def clean_env(monkeypatch):
    # Ensure clean env for each test
    for k in list(os.environ.keys()):
        if k.startswith(("GOOGLE_", "EMBEDDINGS_PROVIDER")):
            monkeypatch.delenv(k, raising=False)
    yield


def install_fakes(monkeypatch, *, with_vertex=True, with_genai=False):
    """
    Preload sys.modules with fake provider SDKs so the module imports our fakes.
    """
    # Vertex fake (class must be accessible as VertexAIEmbeddings)
    if with_vertex:
        class FakeVertexEmb:
            def __init__(self, **kwargs):
                self.kwargs = kwargs
        monkeypatch.setitem(
            sys.modules,
            "langchain_google_vertexai",
            SimpleNamespace(VertexAIEmbeddings=FakeVertexEmb),
        )
    else:
        monkeypatch.delitem(sys.modules, "langchain_google_vertexai", raising=False)

    # GenAI fake (class must be GoogleGenerativeAIEmbeddings)
    if with_genai:
        class FakeGenAIEmb:
            def __init__(self, **kwargs):
                self.kwargs = kwargs
        monkeypatch.setitem(
            sys.modules,
            "langchain_google_genai",
            SimpleNamespace(GoogleGenerativeAIEmbeddings=FakeGenAIEmb),
        )
    else:
        monkeypatch.delitem(sys.modules, "langchain_google_genai", raising=False)


def test_vertex_happy_path(monkeypatch):
    install_fakes(monkeypatch, with_vertex=True, with_genai=False)

    # Defaults to vertex when EMBEDDINGS_PROVIDER unset
    monkeypatch.setenv("GOOGLE_CLOUD_PROJECT", "proj-123")
    monkeypatch.setenv("GOOGLE_CLOUD_LOCATION", "us-central1")

    mod = fresh_import()
    emb = mod.get_embeddings()

    # Embeddings instance from our fake, with correct kwargs
    assert hasattr(emb, "kwargs")
    assert emb.kwargs["model_name"] == "text-embedding-004"
    assert emb.kwargs["project"] == "proj-123"
    assert emb.kwargs["location"] == "us-central1"


def test_vertex_missing_project_raises_keyerror(monkeypatch):
    install_fakes(monkeypatch, with_vertex=True, with_genai=False)

    monkeypatch.setenv("EMBEDDINGS_PROVIDER", "vertex")
    # Intentionally omit GOOGLE_CLOUD_PROJECT

    with pytest.raises(KeyError) as exc:
        fresh_import().get_embeddings()
    assert "GOOGLE_CLOUD_PROJECT" in str(exc.value)


def test_genai_happy_path(monkeypatch):
    install_fakes(monkeypatch, with_vertex=False, with_genai=True)

    monkeypatch.setenv("EMBEDDINGS_PROVIDER", "genai")
    monkeypatch.setenv("GOOGLE_API_KEY", "fake-key-123")

    mod = fresh_import()
    emb = mod.get_embeddings()

    assert hasattr(emb, "kwargs")
    assert emb.kwargs["model"] == "models/embedding-001"
    assert emb.kwargs["google_api_key"] == "fake-key-123"


def test_genai_missing_package_raises(monkeypatch):
    # Vertex can exist; we want ONLY genai import to fail
    install_fakes(monkeypatch, with_vertex=True, with_genai=False)

    # Make importing langchain_google_genai raise ImportError even if installed
    import builtins as _builtins
    real_import = _builtins.__import__

    def fake_import(name, *args, **kwargs):
        if name == "langchain_google_genai":
            raise ImportError("simulated missing package")
        return real_import(name, *args, **kwargs)

    monkeypatch.setattr(_builtins, "__import__", fake_import)

    monkeypatch.setenv("EMBEDDINGS_PROVIDER", "genai")
    monkeypatch.setenv("GOOGLE_API_KEY", "fake-key-123")

    with pytest.raises(RuntimeError) as exc:
        fresh_import().get_embeddings()
    assert "langchain-google-genai not installed" in str(exc.value)



def test_genai_missing_key_raises(monkeypatch):
    install_fakes(monkeypatch, with_vertex=False, with_genai=True)

    monkeypatch.setenv("EMBEDDINGS_PROVIDER", "genai")
    # Intentionally omit GOOGLE_API_KEY

    with pytest.raises(RuntimeError) as exc:
        fresh_import().get_embeddings()
    assert "GOOGLE_API_KEY is not set" in str(exc.value)


def test_unsupported_provider_raises(monkeypatch):
    install_fakes(monkeypatch, with_vertex=True, with_genai=True)

    monkeypatch.setenv("EMBEDDINGS_PROVIDER", "nope")

    with pytest.raises(ValueError) as exc:
        fresh_import().get_embeddings()
    assert "Unsupported EMBEDDINGS_PROVIDER" in str(exc.value)
