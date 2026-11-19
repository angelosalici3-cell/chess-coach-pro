"""Cache in memoria a scadenza breve: evita di rifare le stesse query a ogni apertura dell'app."""
import threading
import time

_lock = threading.Lock()
_store: dict[tuple, tuple[float, object]] = {}
MAX_ITEMS = 3000


def get(key: tuple):
    with _lock:
        hit = _store.get(key)
        if hit and hit[0] > time.monotonic():
            return hit[1]
        _store.pop(key, None)
        return None


def put(key: tuple, value, ttl: float) -> None:
    with _lock:
        if len(_store) >= MAX_ITEMS:
            now = time.monotonic()
            for k in [k for k, (exp, _) in _store.items() if exp <= now] or list(_store)[: MAX_ITEMS // 4]:
                _store.pop(k, None)
        _store[key] = (time.monotonic() + ttl, value)


def bust(email: str) -> None:
    """Dopo una modifica (sync, piano, lezione...) i dati dell'utente si rileggono subito."""
    with _lock:
        for k in [k for k in _store if len(k) > 1 and k[1] == email]:
            _store.pop(k, None)
