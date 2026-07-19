import asyncio
from collections import defaultdict
from datetime import datetime, timedelta


class RateLimiter:
    def __init__(self, max_requests: int = 30, window_seconds: int = 60):
        self.max_requests = max_requests
        self.window_seconds = window_seconds
        self.requests: dict[str, list[datetime]] = defaultdict(list)
        self._lock = asyncio.Lock()

    async def check(self, user_id: str, tool_name: str) -> tuple[bool, int]:
        key = f"{user_id}:{tool_name}"
        now = datetime.utcnow()
        window_start = now - timedelta(seconds=self.window_seconds)

        async with self._lock:
            self.requests[key] = [t for t in self.requests[key] if t > window_start]

            if len(self.requests[key]) >= self.max_requests:
                oldest = min(self.requests[key])
                retry_after = int(
                    (oldest + timedelta(seconds=self.window_seconds) - now).total_seconds()
                )
                return False, max(retry_after, 1)

            self.requests[key].append(now)
            return True, 0


rate_limiter = RateLimiter()
