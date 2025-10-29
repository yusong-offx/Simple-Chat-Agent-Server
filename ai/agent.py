import json
from typing import Any

from langchain_core.messages.human import HumanMessage
from ai.graph import ai_app
from ai.state import AgentState
from pydantic import BaseModel

class StreamingMessage(BaseModel):
    event: str
    data: Any


async def ai_model(session_id: str, user_input: str):
    msgs = ai_app.astream(
        AgentState(messages=[HumanMessage(user_input)]),
        config={"configurable": {"thread_id": session_id}},
        stream_mode="messages"
    )
    async for msg in msgs:
        yield StreamingMessage(
            event="update", data=msg
        ).model_dump_json()

async def ai_model_sync(session_id: str, user_input: str):
    msgs = await ai_app.ainvoke(
        AgentState(messages=[HumanMessage(user_input)]),
        config={"configurable": {"thread_id": session_id}},
    )
    return msgs

def get_session_history(session_id: str):
    return ai_app.aget_state_history(config={"configurable": {"thread_id": session_id}})
