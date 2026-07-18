from __future__ import annotations
import asyncio
import logging
from fastapi import WebSocket

logger = logging.getLogger(__name__)

class ConnectionManager:
    def __init__(self) -> None:
        self.connections: set[WebSocket] = set()

    async def connect(self, websocket: WebSocket) -> None:
        await websocket.accept()
        self.connections.add(websocket)
        logger.info("WebSocket client connected; active=%d", len(self.connections))

    def disconnect(self, websocket: WebSocket) -> None:
        self.connections.discard(websocket)
        logger.info("WebSocket client disconnected; active=%d", len(self.connections))

    async def broadcast(self, event_type: str, data: dict) -> None:
        payload = {"type": event_type, "data": data}
        failed = []
        for socket in list(self.connections):
            try:
                await asyncio.wait_for(socket.send_json(payload), timeout=1)
            except Exception:
                failed.append(socket)
        for socket in failed:
            self.disconnect(socket)
