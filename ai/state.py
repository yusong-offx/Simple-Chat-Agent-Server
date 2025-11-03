from pydantic import BaseModel, Field
from typing import Annotated, List, Optional
from langchain_core.messages import AnyMessage
from langgraph.graph import add_messages

from ai.news.tools.rss_feed import NewsItem


class AgentState(BaseModel):
    messages: Annotated[List[AnyMessage], add_messages] = Field(default_factory=list)
    news: Optional[List[NewsItem]] = Field(default=None)
    route: Optional[str] = Field(default=None)
