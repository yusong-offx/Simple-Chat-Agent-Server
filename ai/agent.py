import json

from langchain_core.messages.human import HumanMessage
from ai.graph import ai_app
from ai.state import AgentState
from pydantic import BaseModel

class StreamingMessage(BaseModel):
    event: str
    data: str


async def ai_model(session_id: str, user_input: str):
    msgs = ai_app.astream_events(
        AgentState(messages=[HumanMessage(user_input)]),
        config={"configurable": {"thread_id": session_id}},
    )
    async for msg in msgs:
        if msg["event"] == "on_chat_model_stream":
            data = msg.get("data", {}).get("chunk")
            content = getattr(data, "content", None)
            if content:
                yield StreamingMessage(
                    event="on_chat_model_stream", data=str(content)
                ).model_dump_json()

        elif msg["event"] == "on_tool_start":
            yield StreamingMessage(
                event="on_tool_start", data=json.dumps(msg["data"].get("input"))
            ).model_dump_json()

        elif msg["event"] == "on_tool_end":
            data = msg.get("data", {}).get("output")
            if data is not None:
                payload = getattr(data, "content", data)
                yield StreamingMessage(
                    event="on_tool_end",
                    data=str(payload),
                ).model_dump_json()

        elif msg["event"] in {"on_chain_error", "on_tool_error"}:
            yield StreamingMessage(event=msg["event"], data=str(msg)).model_dump_json()

async def ai_model_sync(session_id: str, user_input: str):
    msgs = await ai_app.ainvoke(
        AgentState(messages=[HumanMessage(user_input)]),
        config={"configurable": {"thread_id": session_id}},
    )
    return msgs

def get_session_history(session_id: str):
    return ai_app.aget_state_history(config={"configurable": {"thread_id": session_id}})
