import pytest
import pytest_asyncio
import types
from fastapi.testclient import TestClient
from httpx import AsyncClient, ASGITransport

from src import main, validate


# ─── fixture: isolate DB to an in-memory dict ──────────────────────────
@pytest.fixture(autouse=True)
def stub_db(monkeypatch):
    fake_db = {}

    monkeypatch.setattr(main, "read_db", lambda: fake_db)
    monkeypatch.setattr(main, "write_db", lambda db: fake_db.update(db))
    yield fake_db  # tests can inspect / mutate


# ─── fixture: disable SlowAPI middleware (rate-limit) ──────────────────
# @pytest.fixture(autouse=True)
# def disable_limiter(monkeypatch):
#     monkeypatch.setattr(main, "limiter", None, raising=False)


# ─── sync TestClient (simple) ──────────────────────────────────────────
@pytest.fixture
def client():
    return TestClient(main.app)


# ─── async client for websocket / async tests ──────────────────────────
@pytest_asyncio.fixture
async def async_client():
    transport = ASGITransport(app=main.app)
    async with AsyncClient(transport=transport, base_url="http://test") as ac:
        yield ac


@pytest.fixture(autouse=True)
def bypass_init_data(monkeypatch):
    """
    Replace src.validate.get_init_data with a stub that
    trusts whatever comes in and returns an object
    that looks like InitData(user.id = 123).
    """

    class DummyInit:  # mimics InitData interface
        def __init__(self, user_id: int):
            self.user = types.SimpleNamespace(id=user_id)

    def fake_get_init_data(
        raw: str, bot_token: str, *, lifetime: int = 3600, request=None
    ):
        # you could parse raw here; we just hard‑wire user_id=123
        if request is not None:
            request.state.user_id = "123"
        return DummyInit(123)

    monkeypatch.setattr(validate, "get_init_data", fake_get_init_data)
    yield
