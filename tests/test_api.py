from freezegun import freeze_time


def _json(trade_in, **overrides):
    return trade_in(**overrides).model_dump(mode="json")


@freeze_time("2026-11-17")
def test_create_trade_201(client, trade_in):
    r = client.post("/trades", json=_json(trade_in))
    assert r.status_code == 201
    body = r.json()
    assert body["trade_id"] == "T1"
    assert body["version"] == 1
    assert body["expired"] == "N"
    assert body["created_date"] == "2026-11-17"


@freeze_time("2026-11-17")
def test_create_rejects_past_maturity(client, trade_in):
    r = client.post("/trades", json=_json(trade_in, maturity_date="2020-01-01"))
    assert r.status_code == 400
    assert "maturity" in r.json()["detail"].lower()


@freeze_time("2026-11-17")
def test_create_rejects_stale_version(client, trade_in):
    client.post("/trades", json=_json(trade_in, version=2))
    r = client.post("/trades", json=_json(trade_in, version=1))
    assert r.status_code == 400
    assert "version" in r.json()["detail"].lower()


@freeze_time("2026-11-17")
def test_same_version_replaces_in_place(client, trade_in):
    client.post("/trades", json=_json(trade_in, counter_party_id="CP-1"))
    r = client.post("/trades", json=_json(trade_in, counter_party_id="CP-9"))
    assert r.status_code == 201
    assert r.json()["counter_party_id"] == "CP-9"
    assert len(client.get("/trades").json()) == 1


@freeze_time("2026-11-17")
def test_list_and_get_endpoints(client, trade_in):
    client.post("/trades", json=_json(trade_in, version=1))
    client.post("/trades", json=_json(trade_in, version=2))
    client.post("/trades", json=_json(trade_in, trade_id="T2", version=1))

    assert len(client.get("/trades").json()) == 3

    t1 = client.get("/trades/T1").json()
    assert {t["version"] for t in t1} == {1, 2}

    one = client.get("/trades/T1/2")
    assert one.status_code == 200
    assert one.json()["version"] == 2

    assert client.get("/trades/missing/1").status_code == 404


def test_health(client):
    assert client.get("/health").json() == {"status": "ok"}
