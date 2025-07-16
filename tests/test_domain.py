import time
from src.main import apply_decay


def test_apply_decay_no_time_passed():
    rec = {"happiness": 80, "last_pet": time.time()}
    assert apply_decay(rec)["happiness"] == 80


def test_apply_decay_reduces_happiness(monkeypatch):
    ts = time.time() - 3600 * 3  # 3h ago
    rec = {"happiness": 90, "last_pet": ts}
    out = apply_decay(rec)
    assert out["happiness"] == 90 - 3 * 4  # DECAY_PER_HOUR=4
