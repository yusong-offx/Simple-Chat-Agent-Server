from pydantic import BaseModel, Field
from typing import Dict, Any, Annotated, List
from langchain_core.messages import AnyMessage
from langgraph.graph import add_messages

from ai.news.tools.rss_feed import NewsItem


class AgentState(BaseModel):
    messages: Annotated[List[AnyMessage], add_messages] = Field(default_factory=list)
    news: List[NewsItem]| None = Field(default=None)
    route: str | None = Field(default=None)
