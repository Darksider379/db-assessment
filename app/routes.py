from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

from app.db import Trade
from app.schemas import TradeIn, TradeOut
from app.service import save_trade


def build_router(get_db) -> APIRouter:
    router = APIRouter()
    Db = Annotated[Session, Depends(get_db)]

    @router.post("/trades", response_model=TradeOut, status_code=status.HTTP_201_CREATED)
    def create_trade(trade_in: TradeIn, db: Db) -> Trade:
        return save_trade(db, trade_in)

    @router.get("/trades", response_model=list[TradeOut])
    def list_trades(db: Db) -> list[Trade]:
        return db.query(Trade).order_by(Trade.trade_id, Trade.version).all()

    @router.get("/trades/{trade_id}", response_model=list[TradeOut])
    def get_trade_versions(trade_id: str, db: Db) -> list[Trade]:
        rows = db.query(Trade).filter_by(trade_id=trade_id).order_by(Trade.version).all()
        if not rows:
            raise HTTPException(status_code=404, detail=f"Trade {trade_id} not found")
        return rows

    @router.get("/trades/{trade_id}/{version}", response_model=TradeOut)
    def get_trade(trade_id: str, version: int, db: Db) -> Trade:
        trade = db.get(Trade, (trade_id, version))
        if trade is None:
            raise HTTPException(status_code=404, detail=f"Trade {trade_id} v{version} not found")
        return trade

    @router.get("/health")
    def health() -> dict[str, str]:
        return {"status": "ok"}

    return router
