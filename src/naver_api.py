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
    수집 윈도우: 전날 10:00 KST ~ 실행 시각
    - 오전 7시 실행 → 전날 10:00 ~ 오늘 07:00
    - 오전 10시 실행 → 전날 10:00 ~ 오늘 10:00
    - 오후 3시 실행  → 전날 10:00 ~ 오늘 15:00
    """
    run_kst = run_date.astimezone(KST)
    yesterday = run_kst.date() - timedelta(days=1)
    window_start = datetime(yesterday.year, yesterday.month, yesterday.day, 10, 0, 0, tzinfo=KST)
    return window_start <= article_dt <= run_kst


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
            "display": 100,  # 최대치 요청 후 날짜 필터로 추림
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
