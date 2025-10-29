from uuid import UUID
from typing import Any

from fastapi import FastAPI, Request, Path, Response
from pydantic import BaseModel, Field, ConfigDict

from sse_starlette.sse import EventSourceResponse
from ai.agent import ai_model, get_session_history


tags_metadata = [
    {"name": "Health", "description": "Liveness/health checks."},
    {"name": "Sessions", "description": "Session-scoped history and state."},
    {"name": "Talk", "description": "SSE streaming chat with the agents."},
]

app = FastAPI(
    title="Simple Agent Server",
    version="0.1.0",
    description=(
        "LangGraph 기반 멀티 에이전트(라우팅/뉴스/요약) + LangChain 도구를 "
        "FastAPI로 스트리밍(SSE) 서빙합니다."
    ),
    openapi_tags=tags_metadata,
    docs_url="/docs",
    redoc_url="/redoc",
    openapi_url="/openapi.json",
)


@app.get("/health", tags=["Health"], summary="Liveness probe", response_model=dict[str, str])
async def health() -> dict[str, str]:
    """Simple liveness endpoint used by local/dev environments."""
    return {"status": "ok"}

@app.get(
    "/{session_id}",
    tags=["Sessions"],
    summary="Get session history",
    responses={
        200: {
            "description": "List of state history snapshots for the session.",
            "content": {
                "application/json": {
                    "examples": {
                        "empty": {"value": []},
                        "sample": {
                            "value": [
                                {"ts": "2025-10-29T12:00:00Z", "state": {"route": "chat_agent"}}
                            ]
                        },
                    }
                }
            },
        },
        204: {
            "description" : "no history"
        }
    },
)
async def get_chat_history(
    session_id: UUID = Path(..., description="UUID v4 session identifier")
):
    """Return session-scoped state history. Ephemeral (process memory)."""

    # return [history async for history in get_chat_history(session_id)]
    history = await anext(get_session_history(session_id), None)
    if history is None:
        return Response(status_code=204)
    return history.values['messages']
    


class ChatRequest(BaseModel):
    """Request schema for SSE chat."""

    message: str = Field(description="User message to the agent.")
    model_config = ConfigDict(
        json_schema_extra={
            "examples": [
                {"message": "미국 테크 뉴스 3개만 요약해줘"},
                {"message": "127.0.0.1 시간/위치 알려줘"},
            ]
        }
    )

@app.post(
    "/{session_id}",
    response_class=EventSourceResponse,
    tags=["Talk"],
    summary="Stream agent response (SSE)",
    responses={
        200: {
            "description": "Server-Sent Events stream (one event per message).",
            "content": {
                "text/event-stream": {
                    "schema": {"type": "string"},
                    "examples": {
                        "token": {"value": "event: on_chat_model_stream\ndata: 토큰...\n\n"},
                        "tool": {"value": "event: on_tool_end\ndata: {...}\n\n"},
                    },
                }
            },
        }
    },
)
async def talk_to_llm(
    session_id: UUID = Path(..., description="UUID v4 session identifier"),
    user_message: ChatRequest = ...,  # JSON body
    request: Request = ...,  # reserved for future middleware usage
):
    """Starts an SSE stream that emits model tokens and tool events for the session."""
    return EventSourceResponse(ai_model(session_id, user_message.message))
