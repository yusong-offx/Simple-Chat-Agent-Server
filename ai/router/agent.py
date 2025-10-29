from langchain.chat_models.base import BaseChatModel
from langchain.agents import create_agent
from pydantic import BaseModel
from ai.state import AgentState
from typing import Literal


class RouteResponseFormat(BaseModel):
    router: Literal["chat_agent", "news_agent"]


class RouterAgent:
    __instruction = """
    당신은 '대화 라우터(Dialog Router)'입니다. 사용자의 최신 메시지(맥락 포함)를 읽고
    다음 단계로 보낼 에이전트를 정확히 하나 선택하세요. 가능한 값은:
    - chat_agent: 일반 대화, 정보 질의, 도구(web 검색 등) 활용이 필요한 경우
    - news_agent: 뉴스(헤드라인, 카테고리, 특정 매체/국가) 조회가 필요한 경우

    판별 지침
    - 사용자가 "뉴스/헤드라인/기사/NYT/코리아타임스/RSS/피드" 등 뉴스 탐색을 요청 → news_agent
    - 그 밖의 일반적인 요청, 잡담, 설명 요구, 계산/검색 등 → chat_agent

    출력 형식(중요)
    - 아래 JSON 스키마를 정확히 따르세요: {"router": "chat_agent" | "news_agent"}
    - 추가 필드/설명/코드블록 없이 JSON만 반환합니다.
    - 예시: {"router": "news_agent"}
    """

    def __init__(self, model: BaseChatModel) -> None:
        self.__model = create_agent(
            model=model,
            system_prompt=self.__instruction,
            response_format=RouteResponseFormat,
        )

    async def run(self, state: AgentState):
        # LLM으로 마지막 메시지를 기준으로 라우팅 판단
        resp = await self.__model.ainvoke({"messages": state.messages[-1]})
        return {"route": resp["structured_response"].router}

    def edge_condition(self, state: AgentState) -> str:
        return state.route
