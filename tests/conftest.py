from datetime import date

import pytest
from fastapi.testclient import TestClient

from app.db import Trade
from app.main import create_app
from app.schemas import TradeIn


@pytest.fixture
def app(monkeypatch):
    monkeypatch.setenv("EXPIRY_INTERVAL_MINUTES", "0")
    return create_app(db_url="sqlite:///:memory:")


@pytest.fixture
def client(app):
    return TestClient(app)


@pytest.fixture
def db(app):
    session = app.state.SessionLocal()
    try:
        yield session
    finally:
        session.close()


_TRADE_IN_DEFAULTS = {
    "trade_id": "T1",
    "version": 1,
    "counter_party_id": "CP-1",
    "portfolio_id": "B1",
    "maturity_date": date(2027, 5, 20),
}

_TRADE_ORM_DEFAULTS = {
    **_TRADE_IN_DEFAULTS,
    "created_date": date(2026, 1, 1),
    "expired": "N",
}


@pytest.fixture
def trade_in():
    def _make(**overrides) -> TradeIn:
        return TradeIn(**{**_TRADE_IN_DEFAULTS, **overrides})
    return _make


@pytest.fixture
def make_trade():
    def _make(**overrides) -> Trade:
        return Trade(**{**_TRADE_ORM_DEFAULTS, **overrides})
    return _make
