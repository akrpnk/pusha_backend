"""
FastAPI back-end for the Telegram “Tamagotchi Cat” Mini-App
────────────────────────────────────────────────────────────
• Validates Telegram Web-App initData with init-data-py
• Stores per-user state in a JSON file (upgradeable to DB later)
• Exposes three endpoints:
      POST /state   – read (with decay)
      POST /pet     – write
      POST /webhook – Telegram bot updates
• Loads secrets from a .env file in development
"""

from __future__ import annotations

import json
import os
import time
from pathlib import Path
from typing import Dict, Any

from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.exceptions import RequestValidationError
from fastapi.responses import JSONResponse
from pydantic import BaseModel, Field
from dotenv import load_dotenv

from .validate import get_init_data

from slowapi import Limiter
from slowapi.util import get_remote_address
from slowapi.errors import RateLimitExceeded
from slowapi.middleware import SlowAPIMiddleware

# ──────────────────────────────────────────────────────────
# 1.  Environment & configuration
# ──────────────────────────────────────────────────────────
ROOT_DIR = Path(__file__).parent.parent  # project root “…/”
ENV_FILE = ROOT_DIR / ".env"

load_dotenv(ENV_FILE, override=False)  # no-op if vars already set

BOT_TOKEN: str = os.environ["BOT_TOKEN"]
ALLOWED_ORIGIN: str = os.getenv(  # where the Mini-App is hosted
    "ALLOWED_ORIGIN", "https://akrpnk.github.io"
)

STATE_FILE = ROOT_DIR / "state.json"
STATE_FILE.touch(exist_ok=True)  # ensure the file is present


# ──────────────────────────────────────────────────────────
# 2.  FastAPI app + CORS
# ──────────────────────────────────────────────────────────

app = FastAPI(title="Pusha API", version="1.1")

app.add_middleware(
    CORSMiddleware,
    allow_origins=[ALLOWED_ORIGIN],
    allow_methods=["POST"],
    allow_headers=["*"],
)


def key_by_user_id(request):
    res = getattr(request.state, "user_id", get_remote_address(request))
    print(res)
    return res


limiter = Limiter(
    key_func=key_by_user_id,
    default_limits=["1/second"],
)

app.state.limiter = limiter


def ratelimit_handler(request, exc: RateLimitExceeded):
    resp = JSONResponse(
        status_code=429,
        content={"detail": "Too many pats – wait a sec 🐢"},
    )
    resp.headers["Access-Control-Allow-Origin"] = ALLOWED_ORIGIN
    resp.headers["Access-Control-Allow-Credentials"] = "true"
    return resp


app.add_exception_handler(RateLimitExceeded, ratelimit_handler)
app.add_middleware(SlowAPIMiddleware)


@app.exception_handler(RequestValidationError)
async def debug_validation(request: Request, exc: RequestValidationError):
    print("⚠️  Validation error. Raw body:", await request.body())
    print("⚠️  Details:", exc.errors())
    return JSONResponse(status_code=422, content={"detail": exc.errors()})


# ──────────────────────────────────────────────────────────
# 3.  Pydantic models  (request / response)
# ──────────────────────────────────────────────────────────
class InitPayload(BaseModel):
    initData: str = Field(..., description="Raw query string from WebApp")


class StateOut(BaseModel):
    happiness: int = Field(ge=0, le=100)
    last_pet: float = Field(..., description="Unix timestamp (seconds)")


# ──────────────────────────────────────────────────────────
# 4.  Persistence helpers – naive JSON, good enough for dev
# ──────────────────────────────────────────────────────────
def read_db() -> Dict[str, Any]:
    try:
        with STATE_FILE.open() as f:
            return json.load(f)
    except json.JSONDecodeError:
        return {}


def write_db(db: Dict[str, Any]) -> None:
    STATE_FILE.write_text(json.dumps(db, indent=1))


def default_state() -> Dict[str, Any]:
    now = time.time()
    return {"happiness": 80, "last_pet": now}


# ──────────────────────────────────────────────────────────
# 5.  Domain logic helpers
# ──────────────────────────────────────────────────────────
DECAY_PER_HOUR = 4
BOOST_ON_PET = 5


def apply_decay(rec: Dict[str, Any]) -> Dict[str, Any]:
    now = time.time()
    hours = (now - rec["last_pet"]) / 3600
    rec["happiness"] = max(0, rec["happiness"] - int(hours * DECAY_PER_HOUR))
    return rec


# ──────────────────────────────────────────────────────────
# 6.  API routes
# ──────────────────────────────────────────────────────────
@app.post("/state", response_model=StateOut)
async def state(payload: InitPayload):
    init = get_init_data(payload.initData, BOT_TOKEN)
    uid = str(init.user.id)

    db = read_db()
    rec = db.get(uid, default_state())
    rec = apply_decay(rec)

    return rec


@app.post("/pet", response_model=StateOut)
async def pet(payload: InitPayload):
    init = get_init_data(payload.initData, BOT_TOKEN)
    uid = str(init.user.id)

    db = read_db()
    rec = db.get(uid, default_state())
    rec = apply_decay(rec)  # decay first
    rec["happiness"] = min(100, rec["happiness"] + BOOST_ON_PET)
    rec["last_pet"] = time.time()

    db[uid] = rec
    write_db(db)
    return rec


@app.post("/webhook")
async def telegram_webhook(request: Request):
    """
    Minimal webhook handler.  Right now we just say “OK” so Telegram stops
    retrying.  You can parse JSON and handle /start or other commands here.
    """
    await request.json()  # you might log or route later
    return {"ok": True}


# ──────────────────────────────────────────────────────────
# 7.  Local dev entry point
# ──────────────────────────────────────────────────────────
if __name__ == "__main__":
    import uvicorn

    uvicorn.run(
        "main:app",
        host="127.0.0.1",
        port=8000,
        reload=True,  # auto-reload on code change
        log_level="info",
    )
