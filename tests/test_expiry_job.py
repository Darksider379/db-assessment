from datetime import date

from freezegun import freeze_time

from app.db import Trade
from app.service import expire_matured_trades


@freeze_time("2026-05-21")
def test_flags_only_past_maturity_trades(db, make_trade):
    db.add_all([
        make_trade(trade_id="A", maturity_date=date(2026, 5, 20)),  # past
        make_trade(trade_id="B", maturity_date=date(2027, 1, 1)),   # future
        make_trade(trade_id="C", maturity_date=date(2026, 5, 21)),  # today
    ])
    db.commit()

    changed = expire_matured_trades(db)

    assert changed == 1
    assert db.get(Trade, ("A", 1)).expired == "Y"
    assert db.get(Trade, ("B", 1)).expired == "N"
    assert db.get(Trade, ("C", 1)).expired == "N"


@freeze_time("2026-05-21")
def test_idempotent(db, make_trade):
    db.add(make_trade(trade_id="A", maturity_date=date(2026, 5, 20)))
    db.commit()

    assert expire_matured_trades(db) == 1
    assert expire_matured_trades(db) == 0
