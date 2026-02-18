import asyncio
import json
from typing import Set
from fastapi import WebSocket

class EventBus:
    def __init__(self) -> None:
        self._clients: Set[WebSocket] = set()
        self._lock = asyncio.Lock()

    async def connect(self, ws: WebSocket) -> None:
        await ws.accept()
        async with self._lock:
            self._clients.add(ws)

    async def disconnect(self, ws: WebSocket) -> None:
        async with self._lock:
            self._clients.discard(ws)

    async def broadcast(self, event: dict) -> None:
        msg = json.dumps(event, default=str)
        stale = []
        async with self._lock:
            for ws in self._clients:
                try:
                    await ws.send_text(msg)
                except Exception:
                    stale.append(ws)
            for ws in stale:
                self._clients.discard(ws)

BUS = EventBus()
