from __future__ import annotations

import asyncio
import secrets
from dataclasses import dataclass
from datetime import datetime, timedelta, timezone
from typing import Any

from fastapi import WebSocket
from starlette.websockets import WebSocketDisconnect


def _utcnow() -> datetime:
    return datetime.now(timezone.utc)


@dataclass
class StreamTicketRecord:
    current_user: dict[str, Any]
    expires_at: datetime


class OperatorStreamHub:
    def __init__(self) -> None:
        self._tickets: dict[str, StreamTicketRecord] = {}
        self._connections: set[WebSocket] = set()
        self._sequence = 0
        self._loop: asyncio.AbstractEventLoop | None = None

    def issue_ticket(self, current_user: dict[str, Any], *, ttl_seconds: int = 90) -> dict[str, Any]:
        self._prune_tickets()
        ticket = secrets.token_urlsafe(24)
        expires_at = _utcnow() + timedelta(seconds=ttl_seconds)
        self._tickets[ticket] = StreamTicketRecord(
            current_user={
                "username": current_user.get("username"),
                "role": current_user.get("role"),
                "permissions": list(current_user.get("permissions", [])),
            },
            expires_at=expires_at,
        )
        return {
            "ticket": ticket,
            "expires_at": expires_at,
            "heartbeat_interval_ms": 5000,
            "websocket_path": "/api/operator/stream",
        }

    def consume_ticket(self, ticket: str | None) -> dict[str, Any] | None:
        if not ticket:
            return None
        self._prune_tickets()
        record = self._tickets.pop(ticket, None)
        if not record:
            return None
        if record.expires_at <= _utcnow():
            return None
        return record.current_user

    async def connect(self, websocket: WebSocket) -> None:
        await websocket.accept()
        self._loop = asyncio.get_running_loop()
        self._connections.add(websocket)

    async def disconnect(self, websocket: WebSocket) -> None:
        self._connections.discard(websocket)
        try:
            await websocket.close()
        except RuntimeError:
            pass
        except WebSocketDisconnect:
            pass

    async def send_hello(self, websocket: WebSocket) -> None:
        await self._safe_send(
            websocket,
            {
                "event_type": "hello",
                "resource": "system",
                "generated_at": _utcnow().isoformat(),
                "severity": "info",
                "reason": "stream_connected",
                "sequence": self._next_sequence(),
            },
        )

    async def heartbeat_loop(self, websocket: WebSocket, *, interval_seconds: int = 5) -> None:
        try:
            while True:
                await asyncio.sleep(interval_seconds)
                await self._safe_send(
                    websocket,
                    {
                        "event_type": "heartbeat",
                        "resource": "system",
                        "generated_at": _utcnow().isoformat(),
                        "severity": "info",
                        "reason": "keepalive",
                        "sequence": self._next_sequence(),
                    },
                )
        except asyncio.CancelledError:
            raise

    async def broadcast_invalidation(
        self,
        *,
        resource: str,
        entity_id: str | None = None,
        severity: str = "info",
        reason: str | None = None,
    ) -> None:
        payload = {
            "event_type": f"{resource}.updated",
            "resource": resource,
            "entity_id": entity_id,
            "generated_at": _utcnow().isoformat(),
            "severity": severity,
            "reason": reason,
            "sequence": self._next_sequence(),
        }
        stale_connections: list[WebSocket] = []
        for websocket in list(self._connections):
            ok = await self._safe_send(websocket, payload)
            if not ok:
                stale_connections.append(websocket)
        for websocket in stale_connections:
            self._connections.discard(websocket)

    def emit_invalidation(
        self,
        *,
        resource: str,
        entity_id: str | None = None,
        severity: str = "info",
        reason: str | None = None,
    ) -> None:
        coroutine = self.broadcast_invalidation(
            resource=resource,
            entity_id=entity_id,
            severity=severity,
            reason=reason,
        )
        if self._loop and self._loop.is_running():
            asyncio.run_coroutine_threadsafe(coroutine, self._loop)
            return
        asyncio.run(coroutine)

    async def _safe_send(self, websocket: WebSocket, payload: dict[str, Any]) -> bool:
        try:
            await websocket.send_json(payload)
            return True
        except RuntimeError:
            return False
        except WebSocketDisconnect:
            return False

    def _prune_tickets(self) -> None:
        now = _utcnow()
        expired = [ticket for ticket, record in self._tickets.items() if record.expires_at <= now]
        for ticket in expired:
            self._tickets.pop(ticket, None)

    def _next_sequence(self) -> int:
        self._sequence += 1
        return self._sequence


operator_stream_hub = OperatorStreamHub()
