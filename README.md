# Trade Store

REST API that ingests versioned trades, enforces three business rules, and auto-expires matured trades.

## Stack
- **FastAPI** — REST interface
- **SQLAlchemy** + SQLite (swap `TRADE_DB_URL` for Postgres/MySQL)
- **APScheduler** — background job that flips the `expired` flag
- **Pytest** — TDD suite with `freezegun` for deterministic date logic

## Business rules

1. **Version rule** — Reject with an exception any incoming trade whose version is **lower** than the highest stored version for that Trade Id. **Same** version overwrites the existing `(trade_id, version)` record (preserving its original `created_date`). **Higher** version is inserted as a new row.
2. **Maturity rule** — Reject any incoming trade whose `maturity_date` is earlier than today.
3. **Auto-expiry** — A scheduled job flips `expired` to `Y` for any stored trade whose `maturity_date` is in the past.

## Quick start

```bash
python -m venv .venv && source .venv/bin/activate
pip install -e ".[dev]"
uvicorn app.main:create_app --factory --reload
# → http://localhost:8000/docs
```

Environment overrides:

| Var | Default | Purpose |
|---|---|---|
| `TRADE_DB_URL` | `sqlite:///./trades.db` | SQLAlchemy URL |
| `EXPIRY_INTERVAL_MINUTES` | `60` | Auto-expiry scheduler interval (set to `0` to disable the scheduler) |

## API

| Method | Path | Returns |
|---|---|---|
| `POST` | `/trades` | 201 + `TradeOut`, or 400 on rule violation |
| `GET` | `/trades` | all trades |
| `GET` | `/trades/{trade_id}` | every version of one trade |
| `GET` | `/trades/{trade_id}/{version}` | single record, 404 if missing |
| `GET` | `/health` | `{"status": "ok"}` |

Full OpenAPI at `/docs`.

### Example

```bash
curl -X POST localhost:8000/trades -H 'content-type: application/json' -d '{
  "trade_id": "T1", "version": 1,
  "counter_party_id": "CP-1", "portfolio_id": "B1",
  "maturity_date": "2027-05-20"
}'
```

## Tests

```bash
pytest
```

Suite covers each rule in isolation plus the HTTP contract. Coverage gate is 90%.

## CI (`.github/workflows/ci.yml`)

Two parallel jobs on every push/PR:

- **lint-and-test** — `ruff` + full regression suite with coverage
- **vulnerability-scan** — `pip-audit`; build fails on any CRITICAL or HIGH finding (closest CVSS equivalent to "critical/blocker")

## Design

Class diagram: `diagrams/class_diagram.puml`

```
POST /trades ─► TradeRouter ─► save_trade() ─► Trade(ORM) ─► SQLite
                                     │
                                     └─raises─► TradeValidationError (400)   # stale version OR past maturity

BackgroundScheduler ─(interval)─► expire_matured_trades() ─► UPDATE trades SET expired='Y' ...
```

Layout (6 app files, kept deliberately minimal):

```
app/
├── db.py         # SQLAlchemy Base + Trade (composite PK)
├── schemas.py    # Pydantic TradeIn / TradeOut
├── service.py    # business rules + exceptions + expire_matured_trades
├── routes.py     # FastAPI endpoints
└── main.py       # app factory, lifespan, scheduler, exception handlers
```
