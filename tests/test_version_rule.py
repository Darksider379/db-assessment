import pytest
from freezegun import freeze_time

from app.db import Trade
from app.service import TradeValidationError, save_trade


@freeze_time("2026-11-17")
def test_higher_version_inserts_new_row(db, trade_in):
    save_trade(db, trade_in(trade_id="T1", version=1))
    save_trade(db, trade_in(trade_id="T1", version=2))
    rows = db.query(Trade).filter_by(trade_id="T1").order_by(Trade.version).all()
    assert [r.version for r in rows] == [1, 2]


@freeze_time("2026-11-17")
def test_lower_version_rejected(db, trade_in):
    save_trade(db, trade_in(trade_id="T2", version=2))
    with pytest.raises(TradeValidationError):
        save_trade(db, trade_in(trade_id="T2", version=1))


def test_same_version_replaces_preserving_created_date(db, trade_in):
    with freeze_time("2026-01-01"):
        original = save_trade(db, trade_in(counter_party_id="CP-1"))
        original_created = original.created_date
    with freeze_time("2026-06-01"):
        updated = save_trade(db, trade_in(counter_party_id="CP-9"))
    assert updated.counter_party_id == "CP-9"
    assert updated.created_date == original_created
    assert db.query(Trade).filter_by(trade_id="T1").count() == 1


@freeze_time("2026-11-17")
def test_renewing_expired_trade_clears_expiry(db, make_trade, trade_in):
    from datetime import date

    db.add(make_trade(maturity_date=date(2026, 1, 1), expired="Y"))
    db.commit()

    updated = save_trade(db, trade_in())

    assert updated.expired == "N"
    assert updated.maturity_date == trade_in().maturity_date
    assert updated.created_date == date(2026, 1, 1)
