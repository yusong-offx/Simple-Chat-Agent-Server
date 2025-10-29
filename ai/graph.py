import os

from langgraph.checkpoint.memory import InMemorySaver
from enum import Enum
from langgraph.graph import StateGraph, END
from langchain_google_genai import ChatGoogleGenerativeAI
from dotenv import load_dotenv

from ai.news.agent import NewsAgent
from ai.router.agent import RouterAgent
from ai.state import AgentState
from ai.chat.agent import ChatAgent
from ai.summary.agent import SummaryAgent

_ = load_dotenv()


class NodeName(Enum):
    ROUTER_AGENT = "router_agent"

    CHAT_AGENT = "chat_agent"
    NEWS_AGENT = "news_agent"
    SUMMARY_AGENT = "summary_agent"


__model = os.getenv("BASE_MODEL", "gemini-2.5-flash")
__foundation_model = ChatGoogleGenerativeAI(model=__model)

__router_agent = RouterAgent(__foundation_model)
__chat_agent = ChatAgent(__foundation_model)
__news_agent = NewsAgent(__foundation_model)
__summary_agent = SummaryAgent(__foundation_model)

__workflow = StateGraph(AgentState)

__workflow.add_node(NodeName.ROUTER_AGENT.value, __router_agent.run)
__workflow.add_node(NodeName.CHAT_AGENT.value, __chat_agent.run)
__workflow.add_node(NodeName.NEWS_AGENT.value, __news_agent.run)
__workflow.add_node(NodeName.SUMMARY_AGENT.value, __summary_agent.run)

__workflow.set_entry_point(NodeName.ROUTER_AGENT.value)
__workflow.add_conditional_edges(
    NodeName.ROUTER_AGENT.value,
    __router_agent.edge_condition,
    {
        "chat_agent": NodeName.CHAT_AGENT.value,
        "news_agent": NodeName.NEWS_AGENT.value,
    }
    )

__workflow.add_edge(NodeName.CHAT_AGENT.value, END)
__workflow.add_edge(NodeName.NEWS_AGENT.value, NodeName.SUMMARY_AGENT.value)
__workflow.add_edge(NodeName.SUMMARY_AGENT.value, END)

ai_app = __workflow.compile(checkpointer=InMemorySaver())
