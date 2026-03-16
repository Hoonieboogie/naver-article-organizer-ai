from dataclasses import dataclass
import requests
from bs4 import BeautifulSoup
from google import genai
from google.genai import types


@dataclass
class FetchResult:
    content: str
    source: str  # "url_context" | "bs4" | "description"

    @property
    def is_shallow(self) -> bool:
        return self.source == "description"


class ArticleFetcher:
    BS4_HEADERS = {
        "User-Agent": (
            "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) "
            "AppleWebKit/537.36 (KHTML, like Gecko) "
            "Chrome/122.0.0.0 Safari/537.36"
        )
    }

    def __init__(self, gemini_api_key: str):
        self._client = genai.Client(api_key=gemini_api_key)

    def fetch(self, url: str, fallback_description: str = "") -> FetchResult:
        """3단계 fallback으로 기사 원문을 수집한다."""
        # 1단계: Gemini url_context
        try:
            content = self._fetch_via_url_context(url)
            return FetchResult(content=content, source="url_context")
        except Exception:
            pass

        # 2단계: BS4 크롤링
        try:
            content = self._fetch_via_bs4(url)
            return FetchResult(content=content, source="bs4")
        except Exception:
            pass

        # 3단계: Naver API description (발췌문)
        return FetchResult(content=fallback_description, source="description")

    def _fetch_via_url_context(self, url: str) -> str:
        """Gemini url_context tool로 기사 본문을 가져온다."""
        response = self._client.models.generate_content(
            model="gemini-2.5-flash",
            contents=f"다음 URL의 기사 본문 전체를 그대로 추출해줘. 요약하지 말고 원문 그대로: {url}",
            config=types.GenerateContentConfig(
                tools=[types.Tool(url_context=types.UrlContext())]
            ),
        )
        text = response.text
        if not text or len(text.strip()) < 50:
            raise ValueError("url_context returned empty or too-short content")
        return text.strip()

    def _fetch_via_bs4(self, url: str) -> str:
        """requests + BeautifulSoup4로 기사 본문을 추출한다."""
        resp = requests.get(url, headers=self.BS4_HEADERS, timeout=10)
        resp.raise_for_status()

        soup = BeautifulSoup(resp.text, "lxml")

        # 불필요한 태그 제거
        for tag in soup(["script", "style", "nav", "header", "footer", "aside", "iframe"]):
            tag.decompose()

        # 본문 후보 태그 우선순위 탐색
        for selector in ["article", "div#articleBody", "div.article_body",
                         "div#newsct_article", "div.news_end", "div#content"]:
            el = soup.select_one(selector)
            if el:
                text = el.get_text(separator="\n", strip=True)
                if len(text) > 100:
                    return text

        # fallback: body 전체 텍스트
        text = soup.body.get_text(separator="\n", strip=True) if soup.body else ""
        if len(text) < 100:
            raise ValueError("BS4 extracted content too short")
        return text
