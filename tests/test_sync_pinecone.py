# tests/test_sync_pinecone.py
import importlib
import os
import sys
from types import SimpleNamespace
from unittest.mock import ANY
import pytest

MODPATH = "embedding.sync_pinecone"


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
            "PINECONE_INDEX_NAME",
            "PINECONE_CLOUD",
            "PINECONE_REGION",
            "EMBED_BATCH_SIZE",
        }:
            monkeypatch.delenv(k, raising=False)
    yield


# -------------------------
# Fakes we inject via sys.modules so no network calls happen
# -------------------------

class _FakeIndex:
    def __init__(self, recorder):
        self.recorder = recorder

    def upsert(self, vectors):
        # record upsert call payload
        self.recorder["upserts"].append(list(vectors))


class _FakeDesc:
    def __init__(self, ready=True, dimension=768):
        self._ready = ready
        self.dimension = dimension

    @property
    def status(self):
        return {"ready": self._ready}


class _FakePineconeClient:
    """Mimics the minimal Pinecone client surface used by the module."""
    def __init__(self, recorder, *, initial_exists=False, ready_after=0, dimension=768):
        self.calls = recorder["pc_calls"]
        self._exists = initial_exists
        self._ready_after = ready_after
        self._ready_calls = 0
        self._dimension = dimension
        self._recorder = recorder

    # Methods referenced by the module
    def list_indexes(self):
        self.calls.append(("list_indexes",))
        return [{"name": recorder_get(self._recorder, "index_name", "ecommerce-ai-assistant")}] if self._exists else []

    def create_index(self, name, dimension, metric, spec):
        self.calls.append(("create_index", name, dimension, metric, spec))
        self._exists = True
        self._dimension = dimension
        # once created, we'll allow describe to turn ready based on _ready_after

    def describe_index(self, name):
        self.calls.append(("describe_index", name))
        # simulate readiness after N calls
        if self._ready_calls >= self._ready_after:
            return _FakeDesc(ready=True, dimension=self._dimension)
        else:
            self._ready_calls += 1
            return _FakeDesc(ready=False, dimension=self._dimension)

    def Index(self, name):
        self.calls.append(("Index", name))
        return _FakeIndex(self._recorder)


def recorder_get(rec, key, default=None):
    return rec.get(key, default)


def install_fakes(
    monkeypatch,
    *,
    prisma_products=None,
    pinecone_exists=False,
    pinecone_ready_after=0,
    pinecone_dim=768,
):
    """
    Preload sys.modules with fake implementations so that when sync_pinecone.py
    imports them, it gets our fakes (no network).
    """
    if prisma_products is None:
        prisma_products = [
            SimpleNamespace(model_dump=lambda: {
                "id": 1,
                "name": "Hat",
                "brand": "BrandA",
                "gender": "Unisex",
                "price": "9.99",
                "description": "A lovely hat",
                "primaryColor": "Blue",
            }),
            SimpleNamespace(model_dump=lambda: {
                "id": 2,
                "name": "Shirt",
                "brand": "BrandB",
                "gender": "Male",
                "price": "19.99",
                "description": "Soft cotton shirt",
                "primaryColor": "Green",
            }),
        ]

    recorded = {
        "pc_calls": [],
        "upserts": [],
        "index_name": os.getenv("PINECONE_INDEX_NAME", "ecommerce-ai-assistant"),
    }

    # ---- Fake pinecone (module provides Pinecone class + ServerlessSpec) ----
    def _fake_pinecone_ctor(api_key):
        # api_key is ignored; we want to avoid network calls
        return _FakePineconeClient(
            recorder=recorded,
            initial_exists=pinecone_exists,
            ready_after=pinecone_ready_after,
            dimension=pinecone_dim,
        )

    class _FakeServerlessSpec:
        def __init__(self, cloud, region):
            self.cloud = cloud
            self.region = region

        def __repr__(self):
            return f"ServerlessSpec(cloud={self.cloud}, region={self.region})"

    fake_pinecone_mod = SimpleNamespace(
        Pinecone=_fake_pinecone_ctor,
        ServerlessSpec=_FakeServerlessSpec,
    )
    monkeypatch.setitem(sys.modules, "pinecone", fake_pinecone_mod)

    # ---- Fake providers.embeddings.get_embeddings ----
    class _FakeEmbeddings:
        def __init__(self):
            self.calls = []

        def embed_documents(self, texts):
            self.calls.append(("embed_documents", list(texts)))
            # Return a list of 768-d vectors (matching EMBEDDING_DIM)
            return [[0.1] * 768 for _ in texts]

    fake_providers_embeddings = SimpleNamespace(get_embeddings=lambda: _FakeEmbeddings())
    monkeypatch.setitem(sys.modules, "providers.embeddings", fake_providers_embeddings)

    # ---- Fake prisma client ----
    class _FakePrismaProductSvc:
        async def find_many(self):
            return prisma_products

    class _FakePrisma:
        def __init__(self):
            self.connected = False
            self.product = _FakePrismaProductSvc()

        async def connect(self):
            self.connected = True

        async def disconnect(self):
            self.connected = False

    fake_prisma_mod = SimpleNamespace(Prisma=_FakePrisma)
    monkeypatch.setitem(sys.modules, "prisma", fake_prisma_mod)

    # ---- Stub dotenv.load_dotenv to no-op so .env doesn't leak real keys ----
    monkeypatch.setitem(sys.modules, "dotenv", SimpleNamespace(load_dotenv=lambda *a, **kw: None))

    return recorded


# -------------------------
# Tests
# -------------------------

def test_build_text_none_safe(monkeypatch):
    install_fakes(monkeypatch)
    mod = fresh_import()

    row = {
        "description": None,
        "name": "Name",
        "brand": None,
        "gender": "G",
        "price": None,
        "primaryColor": "Red",
    }
    txt = mod.build_text(row)
    # None fields become empty strings; spaces collapse via join/strip
    assert txt == "Name G Red"


def test_ensure_pinecone_creates_and_waits_ready(monkeypatch):
    # Fresh index: does not exist; becomes ready immediately; dimension OK
    pc_rec = install_fakes(
        monkeypatch,
        pinecone_exists=False,
        pinecone_ready_after=0,
        pinecone_dim=768,
    )
    os.environ["PINECONE_INDEX_NAME"] = "ecommerce-ai-assistant"
    mod = fresh_import()

    # exercise ensure_pinecone_index directly
    pc = mod.Pinecone(api_key="ignored")
    idx = mod.ensure_pinecone_index(pc, "ecommerce-ai-assistant", 768)

    # created?
    assert ("create_index", "ecommerce-ai-assistant", 768, "cosine", ANY) in pc.calls
    # waited + got Index
    assert ("describe_index", "ecommerce-ai-assistant") in pc.calls
    assert ("Index", "ecommerce-ai-assistant") in pc.calls
    assert isinstance(idx, object)


def test_ensure_pinecone_skips_create_if_exists_and_checks_dim(monkeypatch):
    # Index already exists and is ready; dimension matches
    pc_rec = install_fakes(
        monkeypatch,
        pinecone_exists=True,
        pinecone_ready_after=0,
        pinecone_dim=768,
    )
    os.environ["PINECONE_INDEX_NAME"] = "ecommerce-ai-assistant"
    mod = fresh_import()

    pc = mod.Pinecone(api_key="ignored")
    _ = mod.ensure_pinecone_index(pc, "ecommerce-ai-assistant", 768)

    # No create_index since it exists
    assert not any(c[0] == "create_index" for c in pc.calls)
    # Still describes and returns Index
    assert ("describe_index", "ecommerce-ai-assistant") in pc.calls
    assert ("Index", "ecommerce-ai-assistant") in pc.calls


def test_ensure_pinecone_raises_on_dim_mismatch(monkeypatch):
    # Index exists but with wrong dimension → should raise
    pc_rec = install_fakes(
        monkeypatch,
        pinecone_exists=True,
        pinecone_ready_after=0,
        pinecone_dim=512,  # mismatch
    )
    os.environ["PINECONE_INDEX_NAME"] = "ecommerce-ai-assistant"
    mod = fresh_import()

    pc = mod.Pinecone(api_key="ignored")
    with pytest.raises(RuntimeError) as exc:
        mod.ensure_pinecone_index(pc, "ecommerce-ai-assistant", 768)
    assert "dimension=512" in str(exc.value)


@pytest.mark.asyncio
async def test_fetch_products_df_builds_dataframe(monkeypatch):
    install_fakes(monkeypatch)
    mod = fresh_import()

    df = await mod.fetch_products_df()
    # Should have 2 rows per default fake above
    assert list(df.columns) == ["id", "name", "brand", "gender", "price", "description", "primaryColor"]
    assert len(df) == 2
    assert set(df["name"]) == {"Hat", "Shirt"}


def test_main_missing_api_key_raises(monkeypatch):
    install_fakes(monkeypatch)
    # ensure there is no leaked API key from .env
    # (we already stubbed dotenv above; just confirm env is clean)
    os.environ.pop("PINECONE_API_KEY", None)

    mod = fresh_import()
    with pytest.raises(RuntimeError) as exc:
        mod.main()
    assert "PINECONE_API_KEY is not set" in str(exc.value)


def test_main_handles_empty_df(monkeypatch, capsys):
    # Fake Prisma returns empty list → empty DataFrame → should print and return
    install_fakes(monkeypatch, prisma_products=[])
    os.environ["PINECONE_API_KEY"] = "pc_key"

    mod = fresh_import()
    mod.main()

    out = capsys.readouterr().out
    assert "No data found in products; nothing to sync." in out


def test_main_happy_path_batches_upserts(monkeypatch):
    # Use 3 products and batch size 2 → two batches (2 + 1)
    products = [
        SimpleNamespace(model_dump=lambda: {
            "id": 1, "name": "Hat", "brand": "A", "gender": "U",
            "price": "10", "description": "D1", "primaryColor": "Blue",
        }),
        SimpleNamespace(model_dump=lambda: {
            "id": 2, "name": "Shirt", "brand": "B", "gender": "M",
            "price": "20", "description": "D2", "primaryColor": "Green",
        }),
        SimpleNamespace(model_dump=lambda: {
            "id": 3, "name": "Pants", "brand": "C", "gender": "F",
            "price": "30", "description": "D3", "primaryColor": "Red",
        }),
    ]
    rec = install_fakes(monkeypatch, prisma_products=products, pinecone_exists=True, pinecone_ready_after=0)
    os.environ["PINECONE_API_KEY"] = "pc_key"
    os.environ["EMBED_BATCH_SIZE"] = "2"  # batch into 2 + 1

    mod = fresh_import()
    mod.main()

    # Verify two upserts: first with ids 1,2 then 3
    assert len(rec["upserts"]) == 2
    batch1 = rec["upserts"][0]
    batch2 = rec["upserts"][1]

    # Each item is a tuple (id, vector, metadata)
    ids1 = [t[0] for t in batch1]
    ids2 = [t[0] for t in batch2]
    assert ids1 == ["1", "2"]
    assert ids2 == ["3"]

    # Vector length is 768 due to our fake embedding
    assert all(len(t[1]) == 768 for t in batch1 + batch2)

    # Metadata keys present
    for _, _, meta in batch1 + batch2:
        for key in ["id", "name", "description", "brand", "gender", "price", "primaryColor"]:
            assert key in meta
