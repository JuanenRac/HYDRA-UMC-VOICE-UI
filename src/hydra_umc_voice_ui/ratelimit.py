# =============================================================================
# HYDRA-UMC-VOICE-UI - Per-client request limit
# Copyright (C) 2026 JuanenRac (Electro Hobby 3D) <electrohobby3d@gmail.com>
# GPL-3.0 - see LICENSE
# =============================================================================
"""A sliding-window limit of requests per client address.

The used-confirmation list of the gateway is bounded (a token is accepted once), and what is bounded can be
filled: one client that issued and confirmed thousands of tokens inside the 30 seconds they live would make
every other confirmation wait. Limiting how many requests one address may make a minute closes that, without
turning anyone away at a normal pace (a spoken command every few seconds is far below the default). The
number of addresses remembered is bounded too, so the limiter cannot grow without limit either.
"""
from __future__ import annotations

import threading
import time
from collections import OrderedDict, deque
from typing import Callable

DEFAULT_REQUESTS_PER_MINUTE = 120
MAX_TRACKED_CLIENTS = 1024


class ClientRateLimiter:
    def __init__(
        self,
        limit: int = DEFAULT_REQUESTS_PER_MINUTE,
        *,
        window: float = 60.0,
        max_clients: int = MAX_TRACKED_CLIENTS,
        clock: Callable[[], float] = time.monotonic,
    ) -> None:
        if limit < 0:
            raise ValueError("the limit must be zero (no limit) or more")
        self.limit = limit
        self.window = window
        self._max_clients = max_clients
        self._clock = clock
        self._lock = threading.Lock()
        self._seen: OrderedDict[str, deque[float]] = OrderedDict()

    def allow(self, client: str) -> tuple[bool, float]:
        """Count a request of `client`. Returns (allowed, seconds to wait when it is not)."""
        if self.limit == 0:
            return True, 0.0
        now = self._clock()
        with self._lock:
            times = self._seen.get(client)
            if times is None:
                times = deque()
                self._seen[client] = times
                while len(self._seen) > self._max_clients:
                    self._seen.popitem(last=False)  # the client that has been quiet longest is forgotten
            else:
                self._seen.move_to_end(client)
            while times and now - times[0] >= self.window:
                times.popleft()
            if len(times) >= self.limit:
                return False, max(0.0, self.window - (now - times[0]))
            times.append(now)
            return True, 0.0
