from sqlalchemy import CHAR, Column, Date, Index, Integer, String
from sqlalchemy.orm import DeclarativeBase


class Base(DeclarativeBase):
    pass


class Trade(Base):
    __tablename__ = "trades"

    trade_id = Column(String(50), primary_key=True)
    version = Column(Integer, primary_key=True)
    counter_party_id = Column(String(50), nullable=False)
    portfolio_id = Column(String(50), nullable=False)
    maturity_date = Column(Date, nullable=False)
    created_date = Column(Date, nullable=False)
    expired = Column(CHAR(1), nullable=False, default="N")

    __table_args__ = (
        Index("ix_trades_expiry", "maturity_date", "expired"),
    )
