from __future__ import annotations

import json
from typing import Any, AsyncIterator

from langchain_core.messages.human import HumanMessage
from ai.graph import ai_app
from ai.state import AgentState


def _serialize(event: dict[str, Any]) -> dict[str, Any]:
    """Normalize LangGraph astream_events payloads for SSE.

    Returns a dict with keys accepted by EventSourceResponse: {"event", "data"}.
    """
    name = event.get("event") or "message"
    # Keep the payload compact and JSON-serializable
    payload = event.get("data")
    try:
        data = json.dumps(payload, default=str, ensure_ascii=False)
    except Exception:
        data = json.dumps({"repr": repr(payload)}, ensure_ascii=False)
    return {"event": name, "data": data}


async def ai_model(session_id: str, user_input: str) -> AsyncIterator[dict[str, Any]]:
    """Stream LangGraph events as SSE-friendly dicts.

    - Uses astream_events to surface model/tool events (on_chat_model_stream, on_tool_*).
    - Each yielded item is a dict(event=..., data=str) that SSE layer understands.
    """
    async for ev in ai_app.astream_events(
        AgentState(messages=[HumanMessage(user_input)]),
        config={"configurable": {"thread_id": session_id}},
    ):
        yield _serialize(ev)


async def ai_model_sync(session_id: str, user_input: str) -> Any:
    """Non-streaming single-shot invoke for debugging or tests."""
    return await ai_app.ainvoke(
        AgentState(messages=[HumanMessage(user_input)]),
        config={"configurable": {"thread_id": session_id}},
    )


def get_session_history(session_id: str):
    """Return async iterator of state history snapshots for a session."""
    return ai_app.aget_state_history(config={"configurable": {"thread_id": session_id}})
