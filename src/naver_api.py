import re
import requests
from datetime import datetime, timezone, timedelta
from email.utils import parsedate_to_datetime
from urllib.parse import urlparse

KST = timezone(timedelta(hours=9))


def parse_pub_date(pub_date_str: str) -> datetime:
    """네이버 API RFC 822 날짜 문자열 → timezone-aware datetime"""
    dt = parsedate_to_datetime(pub_date_str)
    return dt.astimezone(KST)


def is_in_window(article_dt: datetime, run_date: datetime) -> bool:
    """수집 윈도우: 실행 시각 기준 24시간 전 ~ 실행 시각"""
    window_start = run_date - timedelta(hours=24)
    return window_start <= article_dt <= run_date


def _strip_html(text: str) -> str:
    return re.sub(r"<[^>]+>", "", text)


def _extract_source(url: str) -> str:
    """URL에서 신문사 도메인을 추출한다. (www./news./m. 등 접두사 제거)"""
    try:
        hostname = urlparse(url).hostname or ""
        for prefix in ("www.", "news.", "m.", "view.", "media."):
            if hostname.startswith(prefix):
                hostname = hostname[len(prefix):]
        return hostname
    except Exception:
        return ""


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
        pagination으로 충분한 기사를 확보한다.
        """
        results = []
        start = 1

        while len(results) < max_count and start <= 1000:
            display = min(100, max(max_count * 3, 30))
            params = {
                "query": keyword,
                "display": display,
                "start": start,
                "sort": "date",
            }
            response = requests.get(self.API_URL, headers=self.headers, params=params)
            response.raise_for_status()

            data = response.json()
            items = data.get("items", [])
            if not items:
                break

            found_any_in_window = False
            for item in items:
                try:
                    pub_dt = parse_pub_date(item["pubDate"])
                except Exception:
                    continue

                if pub_dt > run_date:
                    continue

                if not is_in_window(pub_dt, run_date):
                    # 최신순 정렬이므로 윈도우 이전 기사가 나오면 더 볼 필요 없음
                    return results[:max_count]

                found_any_in_window = True
                url = item.get("originallink") or item.get("link", "")
                results.append({
                    "title": _strip_html(item.get("title", "")),
                    "url": url,
                    "description": _strip_html(item.get("description", "")),
                    "published_at": pub_dt.isoformat(),
                    "source_name": _extract_source(url),
                })

                if len(results) >= max_count:
                    return results

            # 이번 페이지에서 윈도우 내 기사가 하나도 없으면 중단
            if not found_any_in_window:
                break

            start += len(items)

        return results[:max_count]
