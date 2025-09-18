import asyncio
import pandas as pd
import numpy as np
import types
import pytest

# --- Fake Prisma client -------------------------------------------------------
class FakeProductModel:
    def __init__(self, recorder):
        self._recorder = recorder

    async def create(self, payload):
        # Mirror Prisma .create signature: create(data: dict)
        # Your code passes dict directly so we just record it.
        self._recorder["creates"].append(payload)
        return {"id": len(self._recorder["creates"]), **payload}


class FakePrisma:
    def __init__(self, recorder):
        self._recorder = recorder
        self._connected = False
        self.product = FakeProductModel(recorder)

    async def connect(self):
        self._recorder["connect_calls"] += 1
        self._connected = True

    async def disconnect(self):
        self._recorder["disconnect_calls"] += 1
        self._connected = False


@pytest.mark.asyncio
async def test_load_csv_to_db_happy_path(monkeypatch, capsys):
    # Arrange a fake DataFrame like your CSV
    df = pd.DataFrame(
        [
            {
                "ProductName": "Air Max 90",
                "ProductBrand": "Nike",
                "Gender": "Men",
                "Price": "129.99",
                "Description": "Classic running shoe",
                "PrimaryColor": "Red",
            },
            {
                "ProductName": "UltraBoost",
                "ProductBrand": np.nan,   # will become None
                "Gender": "Women",
                "Price": np.nan,          # will become None
                "Description": "Cushy daily trainer",
                "PrimaryColor": "Black",
            },
        ]
    )

    # Monkeypatch pandas.read_csv to return our DataFrame
    monkeypatch.setattr("pandas.read_csv", lambda _path: df)

    # Import target module once, then patch its Prisma symbol
    import load_data as mod

    # Recorder to trace calls
    recorder = {"connect_calls": 0, "disconnect_calls": 0, "creates": []}

    # Patch the Prisma class inside the module to our Fake
    monkeypatch.setattr(mod, "Prisma", lambda: FakePrisma(recorder))

    # Act
    await mod.load_csv_to_db()

    # Assert DB lifecycle
    assert recorder["connect_calls"] == 1
    assert recorder["disconnect_calls"] == 1

    # Assert creates (two rows)
    assert len(recorder["creates"]) == 2
    first, second = recorder["creates"]

    assert first == {
        "name": "Air Max 90",
        "brand": "Nike",
        "gender": "Men",
        "price": "129.99",
        "description": "Classic running shoe",
        "primaryColor": "Red",
    }

    # NaNs -> None on brand/price
    assert second == {
        "name": "UltraBoost",
        "brand": None,
        "gender": "Women",
        "price": None,
        "description": "Cushy daily trainer",
        "primaryColor": "Black",
    }

    # Assert printed count
    out = capsys.readouterr().out.strip()
    assert out.endswith("Loaded 2 products into database")


@pytest.mark.asyncio
async def test_load_csv_to_db_empty(monkeypatch, capsys):
    # Empty DataFrame
    df = pd.DataFrame(
        columns=[
            "ProductName",
            "ProductBrand",
            "Gender",
            "Price",
            "Description",
            "PrimaryColor",
        ]
    )

    monkeypatch.setattr("pandas.read_csv", lambda _path: df)

    import load_data as mod

    recorder = {"connect_calls": 0, "disconnect_calls": 0, "creates": []}
    monkeypatch.setattr(mod, "Prisma", lambda: FakePrisma(recorder))

    await mod.load_csv_to_db()

    assert recorder["connect_calls"] == 1
    assert recorder["disconnect_calls"] == 1
    assert recorder["creates"] == []  # no rows

    out = capsys.readouterr().out.strip()
    assert out.endswith("Loaded 0 products into database")
