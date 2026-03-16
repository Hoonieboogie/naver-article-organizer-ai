import re
import requests
from datetime import datetime, timezone, timedelta
from email.utils import parsedate_to_datetime

KST = timezone(timedelta(hours=9))


def parse_pub_date(pub_date_str: str) -> datetime:
    """네이버 API RFC 822 날짜 문자열 → timezone-aware datetime"""
    dt = parsedate_to_datetime(pub_date_str)
    return dt.astimezone(KST)


def is_in_window(article_dt: datetime, run_date: datetime) -> bool:
    """
    수집 윈도우 확인: run_date 기준 KST 당일 00:00 ~ 23:59
    언제 실행해도 오늘 날짜 기사만 수집한다.
    """
    return article_dt.astimezone(KST).date() == run_date.astimezone(KST).date()


def _strip_html(text: str) -> str:
    return re.sub(r"<[^>]+>", "", text)


class NaverNewsClient:
    API_URL = "https://openapi.naver.com/v1/search/news.json"

    def __init__(self, client_id: str, client_secret: str):
        self.headers = {
            "X-Naver-Client-Id": client_id,
            "X-Naver-Client-Secret": client_secret,
        }

    def fetch_articles(self, keyword: str, max_count: int, run_date: datetime) -> list[dict]:
        """
        키워드로 뉴스 검색 후 수집 윈도우 내 기사만 반환.
        최대 max_count개, 정렬: 최신순(date).
        """
        params = {
            "query": keyword,
            "display": min(max_count * 3, 100),  # 필터 후 충분히 남도록 여유있게 요청
            "sort": "date",
        }
        response = requests.get(self.API_URL, headers=self.headers, params=params)
        response.raise_for_status()

        items = response.json().get("items", [])
        results = []
        for item in items:
            try:
                pub_dt = parse_pub_date(item["pubDate"])
            except Exception:
                continue

            if not is_in_window(pub_dt, run_date):
                continue

            results.append({
                "title": _strip_html(item.get("title", "")),
                "url": item.get("originallink") or item.get("link", ""),
                "description": _strip_html(item.get("description", "")),
                "published_at": pub_dt.isoformat(),
            })

            if len(results) >= max_count:
                break

        return results
