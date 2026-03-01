"""WebSocket endpoint for streaming live agent events."""

from __future__ import annotations

import asyncio
import json

from fastapi import APIRouter, WebSocket, WebSocketDisconnect

from bind_tools.api.events import AgentEventBus

router = APIRouter()


@router.websocket("/api/agents/{agent_id}/ws")
async def agent_ws(websocket: WebSocket, agent_id: str):
    """Stream live agent events via WebSocket.

    On connect, sends all buffered history events, then streams new ones.
    """
    await websocket.accept()

    bus = AgentEventBus.get()
    q, history = bus.subscribe(agent_id)

    try:
        # Send buffered history first
        for event in history:
            await websocket.send_json(event)

        # Stream new events
        while True:
            try:
                event = await asyncio.wait_for(q.get(), timeout=30.0)
                await websocket.send_json(event)

                # If this is a "done" event, send it and close
                if event.get("type") == "done":
                    break
            except asyncio.TimeoutError:
                # Send keepalive ping
                await websocket.send_json({"type": "ping"})
    except WebSocketDisconnect:
        pass
    except Exception:
        pass
    finally:
        bus.unsubscribe(agent_id, q)
