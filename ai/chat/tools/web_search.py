from __future__ import annotations

from dotenv import load_dotenv
from langchain_google_community import GoogleSearchAPIWrapper
from langchain_core.tools import tool

load_dotenv()

search_wrapper = GoogleSearchAPIWrapper()


@tool("web_search", parse_docstring=True)
def google_search_tool(query: str) -> str:
    """
    Uses Google Custom Search via langchain_google_community.GoogleSearchAPIWrapper to
        retrieve relevant results for a natural-language query.

    Best for fresh news, official docs, and factual lookups. Prefer precise
    queries

    Args:
        query (str): The exact search query to run. Include key entities and
            constraints

    Returns:
        str: Text produced by the wrapper summarizing top results (titles/snippets/URLs).

    Raises:
        Exception: If the underlying Google API request fails or credentials are missing.

    Examples:
        - "kubernetes.io HorizontalPodAutoscaler v2"
        - "한국은행 기준금리 2025년 10월"
        - "filetype:pdf diffusion transformer paper 2024"
    """

    try:
        return search_wrapper.run(query)
    except Exception as e:
        raise e
