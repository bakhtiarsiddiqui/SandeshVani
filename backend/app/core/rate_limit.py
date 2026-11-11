import hashlib
import hmac
import secrets
import threading
import time


class AuthRecoveryRateLimiter:
    def __init__(
        self,
        *,
        email_limit: int,
        ip_limit: int,
        window_seconds: int,
        max_entries: int = 20_000,
    ) -> None:
        self._email_limit = email_limit
        self._ip_limit = ip_limit
        self._window_seconds = window_seconds
        self._max_entries = max_entries
        self._key = secrets.token_bytes(32)
        self._counts: dict[str, tuple[int, float]] = {}
        self._lock = threading.Lock()

    def allow(self, ip_address: str, email: str) -> bool:
        now = time.monotonic()
        normalized_email = email.strip().lower()
        keys = (
            (self._digest("ip", ip_address), self._ip_limit),
            (self._digest("email", normalized_email), self._email_limit),
        )

        with self._lock:
            self._purge_expired(now)
            new_keys = sum(key not in self._counts for key, _ in keys)
            if len(self._counts) + new_keys > self._max_entries:
                return False
            if any(self._counts.get(key, (0, 0))[0] >= limit for key, limit in keys):
                return False

            for key, _ in keys:
                count, expires_at = self._counts.get(
                    key, (0, now + self._window_seconds)
                )
                self._counts[key] = (count + 1, expires_at)
            return True

    def clear(self) -> None:
        with self._lock:
            self._counts.clear()

    def _digest(self, category: str, value: str) -> str:
        message = f"{category}\0{value}".encode()
        return hmac.new(self._key, message, hashlib.sha256).hexdigest()

    def _purge_expired(self, now: float) -> None:
        expired = [
            key for key, (_, expires_at) in self._counts.items() if expires_at <= now
        ]
        for key in expired:
            del self._counts[key]
