from collections import defaultdict
from dataclasses import dataclass, field

from fastapi import APIRouter, WebSocket, WebSocketDisconnect

router = APIRouter()


@dataclass
class ConnectionManager:
    connections: dict[str, set[WebSocket]] = field(default_factory=lambda: defaultdict(set))

    async def connect(self, organization_id: str, websocket: WebSocket) -> None:
        await websocket.accept()
        self.connections[organization_id].add(websocket)

    def disconnect(self, organization_id: str, websocket: WebSocket) -> None:
        self.connections[organization_id].discard(websocket)

    async def broadcast(self, organization_id: str, payload: dict) -> None:
        stale: list[WebSocket] = []
        for websocket in self.connections[organization_id]:
            try:
                await websocket.send_json(payload)
            except RuntimeError:
                stale.append(websocket)
        for websocket in stale:
            self.disconnect(organization_id, websocket)


manager = ConnectionManager()


@router.websocket("/events/{organization_id}")
async def event_stream(websocket: WebSocket, organization_id: str) -> None:
    await manager.connect(organization_id, websocket)
    try:
        while True:
            message = await websocket.receive_json()
            await manager.broadcast(organization_id, {"type": "client_ping", "payload": message})
    except WebSocketDisconnect:
        manager.disconnect(organization_id, websocket)


@router.websocket("/notifications/{organization_id}")
async def notification_stream(websocket: WebSocket, organization_id: str) -> None:
    await manager.connect(organization_id, websocket)
    try:
        while True:
            await websocket.receive_text()
    except WebSocketDisconnect:
        manager.disconnect(organization_id, websocket)

