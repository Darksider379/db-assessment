from datetime import date

from sqlalchemy import func, select, update
from sqlalchemy.orm import Session

from app.db import Trade
from app.schemas import TradeIn


class TradeValidationError(Exception):
    pass


def save_trade(db: Session, trade_in: TradeIn) -> Trade:
    today = date.today()
    if trade_in.maturity_date < today:
        raise TradeValidationError(
            f"Maturity date {trade_in.maturity_date} is earlier than today ({today})"
        )

    # SQLite has no SELECT FOR UPDATE. Reserve its writer lock before reading
    # the latest version so competing requests cannot validate stale state.
    if db.get_bind().dialect.name == "sqlite":
        connection = db.connection()
        if not connection.connection.driver_connection.in_transaction:
            connection.exec_driver_sql("BEGIN IMMEDIATE")

    max_version = db.scalar(
        select(func.max(Trade.version)).where(Trade.trade_id == trade_in.trade_id)
    )
    if max_version is not None and trade_in.version < max_version:
        raise TradeValidationError(
            f"Incoming version {trade_in.version} is lower than stored version {max_version} "
            f"for trade {trade_in.trade_id}"
        )

    if max_version is not None and trade_in.version == max_version:
        trade = db.get(Trade, (trade_in.trade_id, trade_in.version))
        for field, value in trade_in.model_dump(exclude={"trade_id", "version"}).items():
            setattr(trade, field, value)
        trade.expired = "N"
    else:
        trade = Trade(**trade_in.model_dump(), created_date=today, expired="N")
        db.add(trade)

    db.commit()
    return trade


def expire_matured_trades(db: Session) -> int:
    result = db.execute(
        update(Trade)
        .where(Trade.maturity_date < date.today(), Trade.expired == "N")
        .values(expired="Y")
    )
    db.commit()
    return result.rowcount
