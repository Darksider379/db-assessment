### Start the app
```bash
python -m venv .venv && source .venv/bin/activate
pip install -e ".[dev]"
uvicorn app.main:create_app --factory --reload
# → http://localhost:8000
```

### API endpoints

| Method | Path | Purpose |
|---|---|---|
| `POST` | `/trades` | Create a trade or replace an existing `(trade_id, version)` |
| `GET`  | `/trades` | List all trades |
| `GET`  | `/trades/{trade_id}` | List every version of one trade |
| `GET`  | `/trades/{trade_id}/{version}` | Fetch one specific record |
| `GET`  | `/health` | Liveness check — `{"status":"ok"}` |

Full interactive docs at http://localhost:8000/docs.

(POST curls use `-i` to show the HTTP status line. GET curls pipe to `jq` for pretty JSON — install once with `brew install jq` if missing.)

### Rule 1 — reject lower version, same version replaces

Setup: insert T1 v1 (201), then T1 v2 (201).
```bash
curl -s -i -X POST localhost:8000/trades -H 'content-type: application/json' -d '{
  "trade_id":"T1","version":1,"counter_party_id":"CP-1","portfolio_id":"B1","maturity_date":"2027-05-20"
}'
curl -s -i -X POST localhost:8000/trades -H 'content-type: application/json' -d '{
  "trade_id":"T1","version":2,"counter_party_id":"CP-1","portfolio_id":"B1","maturity_date":"2027-05-20"
}'
```

Lower version — rejected with 400.
```bash
curl -s -i -X POST localhost:8000/trades -H 'content-type: application/json' -d '{
  "trade_id":"T1","version":1,"counter_party_id":"CP-1","portfolio_id":"B1","maturity_date":"2027-05-20"
}'
```

Same version — replaces the existing record (counter-party changes, created_date preserved), returns 201.
```bash
curl -s -i -X POST localhost:8000/trades -H 'content-type: application/json' -d '{
  "trade_id":"T1","version":2,"counter_party_id":"CP-9","portfolio_id":"B1","maturity_date":"2027-05-20"
}'
```

### Rule 2 — reject a trade with a past maturity date (400)
```bash
curl -s -i -X POST localhost:8000/trades -H 'content-type: application/json' -d '{
  "trade_id":"X","version":1,"counter_party_id":"CP-1","portfolio_id":"B1","maturity_date":"2020-01-01"
}'
```

### Rule 3 — auto-mark expired once maturity is surpassed

Rule 2 blocks POSTing a past-maturity trade, so seed one directly, then let the scheduler run.

Stop the server, then seed:
```bash
.venv/bin/python -c "
from datetime import date
from app.main import create_app
from app.db import Trade
s = create_app().state.SessionLocal()
s.add(Trade(trade_id='OLD', version=1, counter_party_id='CP-1', portfolio_id='B1',
            maturity_date=date(2020,1,1), created_date=date(2020,1,1), expired='N'))
s.commit()
"
```

Restart with a 1-minute scheduler interval (`EXPIRY_INTERVAL_MINUTES` controls how often the expiry check runs — default 60, `0` disables it; `1` here so you see the flip in a minute):
```bash
EXPIRY_INTERVAL_MINUTES=1 .venv/bin/uvicorn app.main:create_app --factory
```

After ~60 seconds, fetch the trade — `expired` should be `Y`.
```bash
curl -s localhost:8000/trades/OLD/1 | jq
```

### Read / inspect

List every trade in the store.
```bash
curl -s localhost:8000/trades | jq
```

List every version of one trade.
```bash
curl -s localhost:8000/trades/T1 | jq
```

Fetch a single record by `(trade_id, version)` (404 if not found).
```bash
curl -s localhost:8000/trades/T1/1 | jq
```

Health check.
```bash
curl -s localhost:8000/health | jq
```
