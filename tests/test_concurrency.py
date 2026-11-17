from concurrent.futures import ThreadPoolExecutor
from threading import Event

from freezegun import freeze_time
from sqlalchemy import create_engine, event
from sqlalchemy.orm import sessionmaker

from app.db import Base
from app.service import TradeValidationError, save_trade


@freeze_time("2026-11-17")
def test_version_check_waits_for_pending_writer(tmp_path, make_trade, trade_in):
    engine = create_engine(f"sqlite:///{tmp_path / 'concurrent.db'}")
    Base.metadata.create_all(engine)
    sessions = sessionmaker(bind=engine)
    checking = Event()

    # The pending version 2 is invisible to other readers until commit.
    with sessions() as writer:
        writer.add(make_trade(version=2))
        writer.flush()

        def before_execute(conn, cursor, statement, parameters, context, executemany):
            if statement == "BEGIN IMMEDIATE":
                checking.set()

        def after_execute(conn, cursor, statement, parameters, context, executemany):
            if "max(trades.version)" in statement:
                checking.set()

        event.listen(engine, "before_cursor_execute", before_execute)
        event.listen(engine, "after_cursor_execute", after_execute)

        def submit_lower_version():
            with sessions() as db:
                try:
                    save_trade(db, trade_in(version=1))
                except TradeValidationError:
                    return "rejected"
                return "accepted"

        try:
            with ThreadPoolExecutor(max_workers=1) as executor:
                pending = executor.submit(submit_lower_version)
                try:
                    assert checking.wait(timeout=3)
                finally:
                    writer.commit()
                assert pending.result(timeout=5) == "rejected"
        finally:
            event.remove(engine, "before_cursor_execute", before_execute)
            event.remove(engine, "after_cursor_execute", after_execute)
            engine.dispose()
