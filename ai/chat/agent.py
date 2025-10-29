from langchain.chat_models.base import BaseChatModel
from langchain.agents import create_agent
from ai.state import AgentState
from ai.chat.tools.ip_info import get_ip_info
from ai.chat.tools.web_search import google_search_tool


class ChatAgent:
    __tools = [get_ip_info, google_search_tool]
    __instruction = """
    You are a helpful assistant.
    """

    def __init__(self, model: BaseChatModel) -> None:
        self.__model = create_agent(
            model=model, tools=self.__tools, system_prompt=self.__instruction
        )

    async def run(self, state: AgentState):
        assistant = await self.__model.ainvoke({"messages": state.messages})
        return {"messages": assistant["messages"]}
