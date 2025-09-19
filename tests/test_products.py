# tests/test_products.py
from fastapi import FastAPI
from fastapi.testclient import TestClient
from backend.routes import products as products_router


def build_app() -> FastAPI:
    app = FastAPI()
    app.include_router(products_router.router)
    return app


class Rec:
    def __init__(self, d): self._d = d
    def model_dump(self): return self._d


class FakePrisma:
    def __init__(self, *, connected: bool, rows=None, raise_on_find: bool = False):
        self._connected = connected
        self.connect_calls = 0
        self.disconnect_calls = 0
        rows = rows or []
        raise_flag = raise_on_find

        class _Product:
            async def find_many(_self):
                if raise_flag:
                    raise RuntimeError("kaboom")
                return [Rec(r) for r in rows]

        self.product = _Product()

    def is_connected(self) -> bool:
        return self._connected

    async def connect(self):
        self.connect_calls += 1
        self._connected = True

    async def disconnect(self):
        self.disconnect_calls += 1
        self._connected = False


def test_products_success(monkeypatch):
    """Returns 200 with serialized records; connects/disconnects once when needed."""
    fake = FakePrisma(
        connected=False,
        rows=[{"id": 1, "name": "Vans Authentic"}, {"id": 2, "name": "Stan Smith"}],
    )
    # Replace the whole prisma instance used by the router
    monkeypatch.setattr("backend.routes.products.prisma", fake, raising=True)

    app = build_app()
    with TestClient(app) as client:
        resp = client.get("/products")
        assert resp.status_code == 200
        assert resp.json() == [
            {"id": 1, "name": "Vans Authentic", "price_display": None},
            {"id": 2, "name": "Stan Smith", "price_display": None},
        ]


    assert fake.connect_calls == 1
    assert fake.disconnect_calls == 1


def test_products_db_error(monkeypatch):
    """If Prisma raises, the route returns 500 with 'DB error:' detail."""
    fake = FakePrisma(connected=True, raise_on_find=True)
    monkeypatch.setattr("backend.routes.products.prisma", fake, raising=True)

    app = build_app()
    with TestClient(app) as client:
        resp = client.get("/products")
        assert resp.status_code == 500
        body = resp.json()
        assert body["detail"].startswith("DB error:")

    # Since already connected, startup shouldn't call connect
    assert fake.connect_calls == 0
    assert fake.disconnect_calls == 1  # shutdown still runs


def test_startup_guard_skips_connect_when_already_connected(monkeypatch):
    """Startup hook should not call connect() if is_connected() is True."""
    fake = FakePrisma(connected=True, rows=[])
    monkeypatch.setattr("backend.routes.products.prisma", fake, raising=True)

    app = build_app()
    with TestClient(app) as client:
        resp = client.get("/products")
        assert resp.status_code == 200
        assert resp.json() == []

    assert fake.connect_calls == 0  # guard worked
    assert fake.disconnect_calls == 1
