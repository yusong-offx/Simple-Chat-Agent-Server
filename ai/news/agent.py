from typing import List, Literal
from langchain.chat_models.base import BaseChatModel
from langchain.agents import create_agent
from langchain_core.messages import ToolMessage
from pydantic import BaseModel

from ai.news.tools.rss_feed import RssFeedCollector
from ai.state import AgentState

_RSS_CATALOG = {
    "america": {
        "brand": "The New York Times",
        "base": "https://rss.nytimes.com/services/xml/rss/nyt/",
        "default_feed": "HomePage",
        "feeds": {
            # 핵심 / 일반
            "HomePage": {"slug": "HomePage.xml", "desc": "NYT 메인 톱기사(전 분야)"},
            "World": {"slug": "World.xml", "desc": "세계 뉴스(국제 현안, 지역 분쟁)"},
            "US": {"slug": "US.xml", "desc": "미국 국내 뉴스(연방·주·지역)"},
            "Politics": {"slug": "Politics.xml", "desc": "미국 정치(백악관·의회·선거)"},
            "Business": {"slug": "Business.xml", "desc": "비즈니스·마켓·기업"},
            "Economy": {"slug": "Economy.xml", "desc": "거시경제·고용·인플레이션"},
            "Technology": {"slug": "Technology.xml", "desc": "테크 산업·신제품·플랫폼"},
            "Science": {"slug": "Science.xml", "desc": "과학 연구·우주·생명과학"},
            "Climate": {"slug": "Climate.xml", "desc": "기후·환경(기후위기, 정책)"},
            "Health": {"slug": "Health.xml", "desc": "보건·의료·공중보건"},
            "Sports": {"slug": "Sports.xml", "desc": "미국·세계 스포츠 종합"},
            "Opinion": {"slug": "Opinion.xml", "desc": "사설·칼럼·Op-Ed"},
            # 문화 / 라이프
            "Arts": {"slug": "Arts.xml", "desc": "예술·전시·공연 전반"},
            "ArtandDesign": {"slug": "ArtandDesign.xml", "desc": "시각예술·디자인"},
            "Books": {"slug": "Books.xml", "desc": "서평·신간"},
            "Movies": {"slug": "Movies.xml", "desc": "영화 뉴스·리뷰"},
            "Television": {"slug": "Television.xml", "desc": "TV·스트리밍"},
            "Theater": {"slug": "Theater.xml", "desc": "연극·브로드웨이"},
            "Music": {"slug": "Music.xml", "desc": "음악·팝·클래식"},
            "Style": {"slug": "FashionandStyle.xml", "desc": "스타일·패션·트렌드"},
            "Food": {"slug": "Food.xml", "desc": "음식·요리·식음료"},
            "Travel": {"slug": "Travel.xml", "desc": "여행·가이드"},
            "RealEstate": {"slug": "RealEstate.xml", "desc": "부동산·주거"},
            "NYRegion": {"slug": "NYRegion.xml", "desc": "뉴욕 지역"},
            # 기타 세분화(있으면 사용)
            "Education": {"slug": "Education.xml", "desc": "교육·대학"},
            "Obituaries": {"slug": "Obituaries.xml", "desc": "부고"},
            "Automobiles": {"slug": "Automobiles.xml", "desc": "자동차·모빌리티"},
            "Space": {"slug": "Space.xml", "desc": "우주·항공우주"},
            "PersonalTech": {"slug": "PersonalTech.xml", "desc": "개인기기·하드웨어"},
            "YourMoney": {"slug": "YourMoney.xml", "desc": "개인재무·소비자"},
            "MediaAds": {"slug": "MediaandAdvertising.xml", "desc": "미디어·광고"},
            "SmallBusiness": {"slug": "SmallBusiness.xml", "desc": "중소기업"},
            "Weddings": {"slug": "Weddings.xml", "desc": "웨딩·라이프"},
            "TMagazine": {"slug": "TMagazine.xml", "desc": "매거진(T Magazine)"},
        },
        # LLM이 빠르게 고르도록 간단 키워드(ko/en) → 표준카테고리
        "aliases": {
            # 상위 관심사
            "최신": "HomePage",
            "탑": "HomePage",
            "top stories": "HomePage",
            "세계": "World",
            "국제": "World",
            "미국": "US",
            "us": "US",
            "u.s.": "US",
            "정치": "Politics",
            "politics": "Politics",
            "백악관": "Politics",
            "의회": "Politics",
            "경제": "Economy",
            "거시": "Economy",
            "비즈니스": "Business",
            "기업": "Business",
            "마켓": "Business",
            "기술": "Technology",
            "테크": "Technology",
            "tech": "Technology",
            "과학": "Science",
            "science": "Science",
            "기후": "Climate",
            "환경": "Climate",
            "climate": "Climate",
            "건강": "Health",
            "health": "Health",
            "스포츠": "Sports",
            "sports": "Sports",
            "오피니언": "Opinion",
            "사설": "Opinion",
            "opinion": "Opinion",
            "예술": "Arts",
            "arts": "Arts",
            "책": "Books",
            "books": "Books",
            "영화": "Movies",
            "movie": "Movies",
            "무비": "Movies",
            "tv": "Television",
            "텔레비전": "Television",
            "드라마": "Television",
            "연극": "Theater",
            "theater": "Theater",
            "음악": "Music",
            "music": "Music",
            "스타일": "Style",
            "패션": "Style",
            "style": "Style",
            "음식": "Food",
            "요리": "Food",
            "food": "Food",
            "와인": "Food",
            "여행": "Travel",
            "travel": "Travel",
            "부동산": "RealEstate",
            "real estate": "RealEstate",
            "뉴욕": "NYRegion",
            "ny": "NYRegion",
        },
    },
    "korea": {
        "brand": "The Korea Times",
        "base": "https://feed.koreatimes.co.kr/k/",
        "default_feed": "AllNews",
        "feeds": {
            "AllNews": {"slug": "allnews.xml", "desc": "전체 기사(전 분야)"},
            "SouthKorea": {
                "slug": "southkorea.xml",
                "desc": "한국 국내 뉴스(정치·사회)",
            },
            "ForeignAffairs": {
                "slug": "foreignaffairs.xml",
                "desc": "외교·안보·한미·북핵",
            },
            "World": {"slug": "world.xml", "desc": "세계 뉴스"},
            "Economy": {"slug": "economy.xml", "desc": "거시경제·지표"},
            "Business": {"slug": "business.xml", "desc": "산업·기업·금융"},
            "Lifestyle": {"slug": "lifestyle.xml", "desc": "라이프·트렌드"},
            "Entertainment": {"slug": "entertainment.xml", "desc": "K-팝·영화·TV·연예"},
            "Sports": {"slug": "sports.xml", "desc": "스포츠"},
            "Opinion": {"slug": "opinion.xml", "desc": "오피니언·칼럼"},
            "Video": {"slug": "video.xml", "desc": "동영상"},
            "Photos": {"slug": "photos.xml", "desc": "포토"},
        },
        "aliases": {
            "전체": "AllNews",
            "all": "AllNews",
            "latest": "AllNews",
            "한국": "SouthKorea",
            "국내": "SouthKorea",
            "외교": "ForeignAffairs",
            "안보": "ForeignAffairs",
            "북핵": "ForeignAffairs",
            "세계": "World",
            "국제": "World",
            "경제": "Economy",
            "거시": "Economy",
            "비즈니스": "Business",
            "기업": "Business",
            "산업": "Business",
            "금융": "Business",
            "라이프": "Lifestyle",
            "트렌드": "Lifestyle",
            "생활": "Lifestyle",
            "연예": "Entertainment",
            "k팝": "Entertainment",
            "k-pop": "Entertainment",
            "엔터": "Entertainment",
            "스포츠": "Sports",
            "오피니언": "Opinion",
            "칼럼": "Opinion",
            "비디오": "Video",
            "동영상": "Video",
            "포토": "Photos",
            "사진": "Photos",
        },
    },
}

Feeds = Literal[
    "HomePage", "World", "US", "Politics", "Business", "Economy",
    "Technology", "Science", "Climate", "Health", "Sports", "Opinion",
    "Arts", "ArtandDesign", "Books", "Movies", "Television", "Theater",
    "Music", "Style", "Food", "Travel", "RealEstate", "NYRegion",
    "Education", "Obituaries", "Automobiles", "Space", "PersonalTech",
    "YourMoney", "MediaAds", "SmallBusiness", "Weddings", "TMagazine",
    "AllNews", "SouthKorea", "ForeignAffairs", "World", "Economy",
    "Business", "Lifestyle", "Entertainment", "Sports", "Opinion",
    "Video", "Photos",
]



class FeedResponseFormat(BaseModel):    
    category: List[str]
    


class NewsAgent:
    __instruction = f"RSS_CATALOG = {_RSS_CATALOG}"  + """
    You are News Source Router.
    Your single job: read the latest user message and choose exactly ONE news source and ONE feed KEY from __RSS_CATALOG.
    Then return the selection in a JSON object that matches the response schema.

    How to choose:
    - Available sources are the top‑level keys of __RSS_CATALOG (e.g., "america", "korea").
    - Within the chosen source, determine one feed KEY by matching the user's intent with that source's "aliases" map first, then its "feeds" keys if needed.
    - IMPORTANT: Use the feed KEY itself (e.g., "Politics", "Economy", "AllNews"). Do NOT return a slug like "Politics.xml" or any translated/altered value.

    Disambiguation rules:
    - If the country/region is clearly mentioned (e.g., "미국", "US", "뉴욕타임즈" → america; "한국", "코리아타임스" → korea), select that source.
    - If multiple categories are implied, pick the most specific one (e.g., "미국 정치" → Politics; "한국 경제" → Economy).
    - If no clear category is found, fall back to that source's default_feed KEY.
    - If no source is clear, default to ("america", america.default_feed KEY).

    Output format requirements (important):
    - Return ONLY a JSON object matching the response schema: {"category": [source_key, feed_key]}.
    - No extra fields, no explanations, no code fences, no quotes around the whole JSON.
    - Example of the exact shape: {"category": ["america", "Politics"]}
    - Use the exact feed KEYS from __RSS_CATALOG; do not invent or translate keys.

    Quick mapping hints (non‑exhaustive, you can rely on each source's aliases table embedded above):
    - america: "미국", "US", "u.s.", "뉴욕타임즈" → source "america".
      • 정치/백악관/의회 → Politics
      • 경제 → Economy; 비즈니스/기업/마켓 → Business; 기술/테크 → Technology; 세계/국제 → World; 스포츠 → Sports
      • 모호하면 default_feed = HomePage"
    - korea: "한국", "대한민국", "코리아타임스" → source "korea".
      • 경제 → Economy; 비즈니스/산업/금융 → Business; 연예/K팝 → Entertainment; 세계/국제 → World; 스포츠 → Sports
      • 모호하면 default_feed = AllNews"

    Few-shot examples:
    - User: "최근 미국뉴스에 대해 알려줘" → {"category": ["america", "HomePage"]}
    - User: "한국 경제 소식 요약" → {"category": ["korea", "Economy"]}
    - User: "NYT 기술 기사 보여줘" → {"category": ["america", "Technology"]}
    - User: "한국 전체 최신 기사" → {"category": ["korea", "AllNews"]}
    - User: "미국 스포츠 결과 어때?" → {"category": ["america", "Sports"]}

    Return only the JSON object with the category tuple. No other words.
    """
    

    def __init__(self, model: BaseChatModel) -> None:
        self.__model = create_agent(
            model=model, system_prompt=self.__instruction, response_format=FeedResponseFormat
        )

    async def run(self, state: AgentState):
        assistant = await self.__model.ainvoke({"messages": [state.messages[-1]]})
        feed_category = getattr(assistant.get("structured_response", {}), "category", None)

        if (
            isinstance(feed_category, list)
            and len(feed_category) >= 2
            and feed_category[0] in _RSS_CATALOG
            and feed_category[1] in _RSS_CATALOG[feed_category[0]]["feeds"]
        ):
            base = _RSS_CATALOG[feed_category[0]]["base"]
            slug = _RSS_CATALOG[feed_category[0]]["feeds"][feed_category[1]]["slug"]
            news = await RssFeedCollector([f"{base}{slug}"]).fetch_all()

            # Compact, readable tool messages for streaming
            call_id = f"call_message_from_{state.messages[-1].id}"
            def _fmt(item):
                ts = item.published_at.isoformat() if item.published_at else ""
                summary = (item.summary or "").strip()
                if len(summary) > 300:
                    summary = summary[:297] + "..."
                return f"{ts} | {item.title}\n{summary}\n{item.link}"

            tool_msgs = [ToolMessage(tool_call_id=call_id, content=_fmt(it)) for it in news]
            return {"messages": tool_msgs, "news": news}

        return {"news": None}
