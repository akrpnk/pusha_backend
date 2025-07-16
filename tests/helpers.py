import json
import time
import urllib.parse
import hashlib
import hmac


def make_signed_init_data(user_id: int, bot_token: str) -> str:
    """Return a spec-compliant initData string for tests."""
    # Minimal field set: user, query_id, auth_date
    payload = {
        "user": json.dumps({"id": user_id, "first_name": "Test"}),
        "query_id": "AAA",  # any opaque string
        "auth_date": str(int(time.time())),
    }

    data_check = "\n".join(f"{k}={payload[k]}" for k in sorted(payload))
    secret = hashlib.sha256(bot_token.encode()).digest()
    payload["hash"] = hmac.new(secret, data_check.encode(), hashlib.sha256).hexdigest()

    return urllib.parse.urlencode(payload, quote_via=urllib.parse.quote_plus)
