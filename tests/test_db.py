import importlib
import sys
from types import SimpleNamespace
import pytest

# Your db module might live at "backend.db" or just "db".
CANDIDATE_MODULES = ["backend.db", "db"]

def _fresh_import(modname: str):
    if modname in sys.modules:
        del sys.modules[modname]
    return importlib.import_module(modname)

def _resolve_modpath():
    for name in CANDIDATE_MODULES:
        try:
            return _fresh_import(name), name
        except ModuleNotFoundError:
            continue
    raise RuntimeError("Could not import backend.db or db. Make sure PYTHONPATH includes project root.")

class FakePrisma:
    """Fake Prisma client to avoid real network. Tracks calls + state."""
    def __init__(self):
        self._connected = False
        self.connect_calls = 0
        self.disconnect_calls = 0

    async def connect(self):
        self.connect_calls += 1
        self._connected = True

    async def disconnect(self):
        self.disconnect_calls += 1
        self._connected = False

    def is_connected(self):
        return self._connected


@pytest.fixture(autouse=True)
def inject_fake_prisma(monkeypatch):
    # Provide a fake 'prisma' module so `from prisma import Prisma` uses our stub
    fake_prisma_module = SimpleNamespace(Prisma=FakePrisma)
    monkeypatch.setitem(sys.modules, "prisma", fake_prisma_module)
    yield
    # Cleanup is automatic because pytest resets monkeypatch after each test


@pytest.mark.asyncio
async def test_connect_db_connects_once(monkeypatch):
    mod, _ = _resolve_modpath()

    # After import, module has a singleton `db` created from FakePrisma
    assert hasattr(mod, "db")
    assert mod.db.is_connected() is False

    # First connect -> should call connect()
    await mod.connect_db()
    assert mod.db.is_connected() is True
    assert mod.db.connect_calls == 1

    # Second connect -> should no-op (still 1 call)
    await mod.connect_db()
    assert mod.db.is_connected() is True
    assert mod.db.connect_calls == 1


@pytest.mark.asyncio
async def test_disconnect_db_disconnects_only_when_connected():
    mod, _ = _resolve_modpath()

    # Start disconnected -> disconnect should no-op
    assert mod.db.is_connected() is False
    await mod.disconnect_db()
    assert mod.db.disconnect_calls == 0
    assert mod.db.is_connected() is False

    # Connect then disconnect -> one call each
    await mod.connect_db()
    assert mod.db.is_connected() is True
    await mod.disconnect_db()
    assert mod.db.disconnect_calls == 1
    assert mod.db.is_connected() is False

    # Extra disconnects still no-op
    await mod.disconnect_db()
    assert mod.db.disconnect_calls == 1
    assert mod.db.is_connected() is False
