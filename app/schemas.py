from datetime import date

from pydantic import BaseModel, ConfigDict, Field


class TradeIn(BaseModel):
    trade_id: str = Field(min_length=1, max_length=50)
    version: int = Field(ge=1)
    counter_party_id: str = Field(min_length=1, max_length=50)
    portfolio_id: str = Field(min_length=1, max_length=50)
    maturity_date: date


class TradeOut(TradeIn):
    model_config = ConfigDict(from_attributes=True)

    created_date: date
    expired: str
