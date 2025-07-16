import json
import hashlib
import hmac
import time
import urllib.parse
import uuid

BOT_TOKEN = "test:token"


def signed_init_data(bot_token: str, user_id: int = 123) -> str:
    """
    Return a valid initData string for the given bot token.
    """
    user_json = json.dumps(  # ← MINIFIED
        {"id": user_id, "first_name": "Test"}, separators=(",", ":")  # <-- no spaces
    )
    payload = {
        "query_id": str(uuid.uuid4()),
        "user": user_json,
        "auth_date": str(int(time.time())),
    }

    data_check = "\n".join(f"{k}={v}" for k, v in sorted(payload.items()))
    secret = hashlib.sha256(bot_token.encode()).digest()
    payload["hash"] = hmac.new(secret, data_check.encode(), hashlib.sha256).hexdigest()

    return urllib.parse.urlencode(payload, quote_via=urllib.parse.quote)


def test_pet_endpoint(client):
    body = {"initData": "anything"}

    # first tap
    r1 = client.post("/pet", json=body)
    assert r1.status_code == 200
    assert r1.json()["happiness"] == 85

    # second tap boosts again
    r2 = client.post("/pet", json=body)
    assert r2.json()["happiness"] == 90


def test_state_endpoint(client, stub_db):
    body = {"initData": "anything"}

    # pre-seed DB
    stub_db["123"] = {"happiness": 77, "last_pet": time.time()}

    res = client.post("/state", json=body)
    assert res.status_code == 200
    assert res.json()["happiness"] <= 77
