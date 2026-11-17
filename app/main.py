import os
from contextlib import asynccontextmanager

from apscheduler.schedulers.background import BackgroundScheduler
from fastapi import FastAPI, Request
from fastapi.responses import JSONResponse
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

from app.db import Base
from app.routes import build_router
from app.service import TradeValidationError, expire_matured_trades


def create_app(db_url: str | None = None) -> FastAPI:
    db_url = db_url or os.environ.get("TRADE_DB_URL", "sqlite:///./trades.db")
    engine_kwargs: dict = {}
    if db_url.startswith("sqlite"):
        engine_kwargs["connect_args"] = {"check_same_thread": False}
        if ":memory:" in db_url:
            engine_kwargs["poolclass"] = StaticPool

    engine = create_engine(db_url, **engine_kwargs)
    SessionLocal = sessionmaker(
        bind=engine, autoflush=False, autocommit=False, expire_on_commit=False
    )
    Base.metadata.create_all(engine)

    def get_db():
        session = SessionLocal()
        try:
            yield session
        finally:
            session.close()

    interval_minutes = int(os.environ.get("EXPIRY_INTERVAL_MINUTES", "60"))
    scheduler: BackgroundScheduler | None = None
    if interval_minutes > 0:
        scheduler = BackgroundScheduler()

        def run_expiry():
            session = SessionLocal()
            try:
                expire_matured_trades(session)
            finally:
                session.close()

        scheduler.add_job(run_expiry, "interval", minutes=interval_minutes)

    @asynccontextmanager
    async def lifespan(_: FastAPI):
        if scheduler is not None:
            scheduler.start()
        yield
        if scheduler is not None:
            scheduler.shutdown(wait=False)

    app = FastAPI(title="Trade Store", lifespan=lifespan)
    app.state.SessionLocal = SessionLocal
    app.include_router(build_router(get_db))

    @app.exception_handler(TradeValidationError)
    async def _trade_validation(_: Request, exc: TradeValidationError):
        return JSONResponse(status_code=400, content={"detail": str(exc)})

    return app
