# tests/test_vector_store.py
import builtins
import importlib
import os
import sys
from types import SimpleNamespace
import pytest

MODPATH = "backend.services.vector_store"


def fresh_import():
    """Import the module fresh each time after we prepare sys.modules/env."""
    if MODPATH in sys.modules:
        del sys.modules[MODPATH]
    return importlib.import_module(MODPATH)


@pytest.fixture(autouse=True)
def clean_env(monkeypatch):
    # ensure a clean env for each test
    for k in list(os.environ.keys()):
        if k.startswith(("GOOGLE_", "PINECONE_", "EMBEDDINGS_PROVIDER")) or k in {
            "PINECONE_INDEX_NAME", "PINECONE_NAMESPACE"
        }:
            monkeypatch.delenv(k, raising=False)
    yield


def install_fake_modules(monkeypatch, *, with_vertex=True, with_genai=False):
    """
    Preload sys.modules with fake implementations so that when vector_store.py
    imports them at module import time, it gets our fakes (no network).
    Also, ensure previously-installed fakes are removed if disabled here.
    """
    # --- Record calls to from_existing_index
    recorded = {"from_existing_calls": []}

    class FakeVectorStore:
        @classmethod
        def from_existing_index(cls, **kwargs):
            recorded["from_existing_calls"].append(kwargs)
            return SimpleNamespace(fake="VECTORSTORE")

    # Fake langchain_pinecone
    fake_langchain_pinecone = SimpleNamespace(PineconeVectorStore=FakeVectorStore)
    monkeypatch.setitem(sys.modules, "langchain_pinecone", fake_langchain_pinecone)

    # Fake pinecone client (no HTTP)
    class FakePineconeClient:
        def __init__(self, api_key):
            self.api_key = api_key

    fake_pinecone = SimpleNamespace(Pinecone=FakePineconeClient)
    monkeypatch.setitem(sys.modules, "pinecone", fake_pinecone)

    # Fake embeddings providers
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

    return recorded


def test_vertex_provider_initializes_with_expected_args(monkeypatch):
    rec = install_fake_modules(monkeypatch, with_vertex=True, with_genai=False)

    monkeypatch.setenv("EMBEDDINGS_PROVIDER", "vertex")
    monkeypatch.setenv("GOOGLE_CLOUD_PROJECT", "telmii-dev")
    monkeypatch.setenv("GOOGLE_CLOUD_LOCATION", "us-central1")
    monkeypatch.setenv("PINECONE_API_KEY", "pc_key")
    monkeypatch.setenv("PINECONE_INDEX_NAME", "ecommerce-ai-assistant")
    monkeypatch.setenv("PINECONE_NAMESPACE", "")  # -> None

    mod = fresh_import()

    assert len(rec["from_existing_calls"]) == 1
    call = rec["from_existing_calls"][0]
    assert call["index_name"] == "ecommerce-ai-assistant"
    assert call["namespace"] is None
    assert call["text_key"] == "description"

    emb = call["embedding"]
    assert emb.kwargs["model_name"] == "text-embedding-004"
    assert emb.kwargs["project"] == "telmii-dev"
    assert emb.kwargs["location"] == "us-central1"

    assert hasattr(mod, "pc")
    assert getattr(mod.pc, "api_key", None) == "pc_key"
    assert hasattr(mod, "vectorstore")


def test_genai_provider_initializes_with_expected_args(monkeypatch):
    rec = install_fake_modules(monkeypatch, with_vertex=False, with_genai=True)

    monkeypatch.setenv("EMBEDDINGS_PROVIDER", "genai")
    monkeypatch.setenv("GOOGLE_API_KEY", "fake_api_key")
    monkeypatch.setenv("PINECONE_API_KEY", "pc_key")
    monkeypatch.setenv("PINECONE_INDEX_NAME", "idx")
    monkeypatch.setenv("PINECONE_NAMESPACE", "ns")

    mod = fresh_import()

    assert len(rec["from_existing_calls"]) == 1
    call = rec["from_existing_calls"][0]
    assert call["index_name"] == "idx"
    assert call["namespace"] == "ns"
    assert call["text_key"] == "description"

    emb = call["embedding"]
    assert emb.kwargs["model"] == "models/embedding-001"
    assert emb.kwargs["google_api_key"] == "fake_api_key"

    assert hasattr(mod, "pc")
    assert getattr(mod.pc, "api_key", None) == "pc_key"
    assert hasattr(mod, "vectorstore")


def test_genai_provider_errors_if_package_missing(monkeypatch):
    # Make sure genai isn’t available anywhere
    install_fake_modules(monkeypatch, with_vertex=False, with_genai=False)
    monkeypatch.delitem(sys.modules, "langchain_google_genai", raising=False)

    # Force import of langchain_google_genai to fail even if installed
    real_import = builtins.__import__

    def fake_import(name, *args, **kwargs):
        if name == "langchain_google_genai":
            raise ImportError("forced missing for test")
        return real_import(name, *args, **kwargs)

    monkeypatch.setattr(builtins, "__import__", fake_import)

    monkeypatch.setenv("EMBEDDINGS_PROVIDER", "genai")
    monkeypatch.setenv("GOOGLE_API_KEY", "fake_api_key")
    monkeypatch.setenv("PINECONE_API_KEY", "pc_key")

    with pytest.raises(RuntimeError) as exc:
        fresh_import()
    assert "langchain-google-genai not installed" in str(exc.value)


def test_genai_provider_errors_if_key_missing(monkeypatch):
    install_fake_modules(monkeypatch, with_vertex=False, with_genai=True)

    monkeypatch.setenv("EMBEDDINGS_PROVIDER", "genai")
    monkeypatch.setenv("PINECONE_API_KEY", "pc_key")
    # No GOOGLE_API_KEY

    with pytest.raises(RuntimeError) as exc:
        fresh_import()
    assert "GOOGLE_API_KEY is not set" in str(exc.value)


def test_vertex_provider_errors_if_project_missing(monkeypatch):
    # Install fakes but we will override the vertex import to enforce the failure
    install_fake_modules(monkeypatch, with_vertex=False, with_genai=False)

    # Provider set to vertex, but project/location removed
    monkeypatch.setenv("EMBEDDINGS_PROVIDER", "vertex")
    monkeypatch.setenv("PINECONE_API_KEY", "pc_key")
    monkeypatch.delenv("GOOGLE_CLOUD_PROJECT", raising=False)
    monkeypatch.delenv("GOOGLE_CLOUD_LOCATION", raising=False)

    # Provide a custom fake for langchain_google_vertexai that raises KeyError
    # if 'project' isn't supplied — this mirrors the contract our module expects.
    class EnforcingVertexEmb:
        def __init__(self, **kwargs):
            if "project" not in kwargs or not kwargs["project"]:
                raise KeyError("GOOGLE_CLOUD_PROJECT")
            self.kwargs = kwargs

    monkeypatch.setitem(
        sys.modules,
        "langchain_google_vertexai",
        SimpleNamespace(VertexAIEmbeddings=EnforcingVertexEmb),
    )

    with pytest.raises(KeyError) as exc:
        fresh_import()
    assert "GOOGLE_CLOUD_PROJECT" in str(exc.value)


def test_unsupported_provider(monkeypatch):
    install_fake_modules(monkeypatch, with_vertex=True, with_genai=True)

    monkeypatch.setenv("EMBEDDINGS_PROVIDER", "not-a-provider")
    monkeypatch.setenv("PINECONE_API_KEY", "pc_key")

    with pytest.raises(ValueError) as exc:
        fresh_import()
    assert "Unsupported EMBEDDINGS_PROVIDER" in str(exc.value)
