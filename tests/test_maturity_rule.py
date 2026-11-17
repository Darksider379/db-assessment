from contextlib import nullcontext
from datetime import date

import pytest
from freezegun import freeze_time

from app.db import Trade
from app.service import TradeValidationError, save_trade


@freeze_time("2026-11-17")
@pytest.mark.parametrize(
    "maturity,expect_error",
    [
        (date(2026, 11, 16), True),   # past: reject
        (date(2026, 11, 17), False),  # today: accept
        (date(2030, 1, 1),  False),   # future: accept
    ],
)
def test_maturity_rule(db, trade_in, maturity, expect_error):
    ctx = pytest.raises(TradeValidationError) if expect_error else nullcontext()
    with ctx:
        save_trade(db, trade_in(maturity_date=maturity))
    assert db.query(Trade).count() == (0 if expect_error else 1)
