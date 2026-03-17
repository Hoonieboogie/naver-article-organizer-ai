from unittest.mock import patch, MagicMock
from datetime import datetime, timezone, timedelta
from src.naver_api import NaverNewsClient, parse_pub_date, is_in_window, _extract_source

KST = timezone(timedelta(hours=9))

def test_parse_pub_date_returns_aware_datetime():
    raw = "Mon, 16 Mar 2026 08:30:00 +0900"
    result = parse_pub_date(raw)
    assert result.tzinfo is not None
    assert result.year == 2026
    assert result.month == 3
    assert result.day == 16
    assert result.hour == 8

def test_is_in_window_24h_range():
    # 오후 3시 실행 → 전날 오후 3시 ~ 오늘 오후 3시
    run_date = datetime(2026, 3, 16, 15, 0, 0, tzinfo=KST)
    assert is_in_window(datetime(2026, 3, 16, 8, 0, 0, tzinfo=KST), run_date) is True
    assert is_in_window(datetime(2026, 3, 15, 20, 0, 0, tzinfo=KST), run_date) is True
    # 24시간 이전은 제외
    assert is_in_window(datetime(2026, 3, 15, 14, 0, 0, tzinfo=KST), run_date) is False
    # 실행 시각 이후는 제외
    assert is_in_window(datetime(2026, 3, 16, 16, 0, 0, tzinfo=KST), run_date) is False

def test_is_in_window_boundary():
    run_date = datetime(2026, 3, 16, 10, 0, 0, tzinfo=KST)
    # 정확히 24시간 전은 포함
    assert is_in_window(datetime(2026, 3, 15, 10, 0, 0, tzinfo=KST), run_date) is True
    # 24시간 + 1초 전은 제외
    assert is_in_window(datetime(2026, 3, 15, 9, 59, 59, tzinfo=KST), run_date) is False

def test_extract_source():
    assert _extract_source("https://www.chosun.com/economy/1234") == "chosun.com"
    assert _extract_source("https://news.jtbc.co.kr/article/1234") == "jtbc.co.kr"
    assert _extract_source("https://m.hani.co.kr/article") == "hani.co.kr"
    assert _extract_source("https://biz.heraldcorp.com/article") == "biz.heraldcorp.com"
    assert _extract_source("") == ""

def test_fetch_articles_calls_naver_api(mocker):
    resp1 = MagicMock()
    resp1.json.return_value = {
        "items": [
            {
                "title": "삼성전자 <b>뉴스</b>",
                "link": "https://news.example.com/1",
                "originallink": "https://www.chosun.com/1",
                "description": "삼성전자가 ...",
                "pubDate": "Mon, 16 Mar 2026 08:30:00 +0900"
            }
        ]
    }
    resp1.raise_for_status = MagicMock()
    resp2 = MagicMock()
    resp2.json.return_value = {"items": []}
    resp2.raise_for_status = MagicMock()
    mocker.patch("requests.get", side_effect=[resp1, resp2])

    client = NaverNewsClient(client_id="test_id", client_secret="test_secret")
    run_date = datetime(2026, 3, 16, 10, 0, 0, tzinfo=KST)
    articles = client.fetch_articles("삼성전자", max_count=10, run_date=run_date)

    assert len(articles) == 1
    assert articles[0]["title"] == "삼성전자 뉴스"
    assert articles[0]["url"] == "https://www.chosun.com/1"
    assert articles[0]["description"] == "삼성전자가 ..."
    assert articles[0]["source_name"] == "chosun.com"

def test_fetch_articles_filters_out_of_window(mocker):
    mock_response = MagicMock()
    mock_response.json.return_value = {
        "items": [
            {
                "title": "오래된 기사",
                "link": "https://news.example.com/2",
                "originallink": "https://news.example.com/2",
                "description": "...",
                "pubDate": "Sat, 14 Mar 2026 08:00:00 +0900"
            }
        ]
    }
    mock_response.raise_for_status = MagicMock()
    mocker.patch("requests.get", return_value=mock_response)

    client = NaverNewsClient(client_id="test_id", client_secret="test_secret")
    run_date = datetime(2026, 3, 16, 10, 0, 0, tzinfo=KST)
    articles = client.fetch_articles("삼성전자", max_count=10, run_date=run_date)

    assert len(articles) == 0

def test_fetch_articles_respects_max_count(mocker):
    items = []
    for i in range(10):
        items.append({
            "title": f"기사 {i}",
            "link": f"https://example.com/{i}",
            "originallink": f"https://example.com/{i}",
            "description": "...",
            "pubDate": "Mon, 16 Mar 2026 08:30:00 +0900"
        })
    mock_response = MagicMock()
    mock_response.json.return_value = {"items": items}
    mock_response.raise_for_status = MagicMock()
    mocker.patch("requests.get", return_value=mock_response)

    client = NaverNewsClient(client_id="test_id", client_secret="test_secret")
    run_date = datetime(2026, 3, 16, 10, 0, 0, tzinfo=KST)

    # max_count=3이면 3개만 반환
    articles = client.fetch_articles("삼성전자", max_count=3, run_date=run_date)
    assert len(articles) == 3
