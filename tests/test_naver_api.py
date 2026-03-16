from unittest.mock import patch, MagicMock
from datetime import datetime, timezone, timedelta
from src.naver_api import NaverNewsClient, parse_pub_date, is_in_window

KST = timezone(timedelta(hours=9))

def test_parse_pub_date_returns_aware_datetime():
    raw = "Mon, 16 Mar 2026 08:30:00 +0900"
    result = parse_pub_date(raw)
    assert result.tzinfo is not None
    assert result.year == 2026
    assert result.month == 3
    assert result.day == 16
    assert result.hour == 8

def test_is_in_window_includes_article_in_range():
    run_date = datetime(2026, 3, 16, 10, 0, 0, tzinfo=KST)
    article_dt = datetime(2026, 3, 16, 8, 0, 0, tzinfo=KST)
    assert is_in_window(article_dt, run_date) is True

def test_is_in_window_excludes_article_before_window():
    run_date = datetime(2026, 3, 16, 10, 0, 0, tzinfo=KST)
    article_dt = datetime(2026, 3, 15, 9, 0, 0, tzinfo=KST)
    assert is_in_window(article_dt, run_date) is False

def test_is_in_window_includes_article_same_day_any_hour():
    # 같은 날이면 시간 무관하게 포함 (오전/오후 모두)
    run_date = datetime(2026, 3, 16, 10, 0, 0, tzinfo=KST)
    article_dt = datetime(2026, 3, 16, 22, 0, 0, tzinfo=KST)
    assert is_in_window(article_dt, run_date) is True

def test_is_in_window_excludes_different_date():
    run_date = datetime(2026, 3, 16, 10, 0, 0, tzinfo=KST)
    article_dt = datetime(2026, 3, 17, 0, 30, 0, tzinfo=KST)
    assert is_in_window(article_dt, run_date) is False

def test_fetch_articles_calls_naver_api(mocker):
    mock_response = MagicMock()
    mock_response.json.return_value = {
        "items": [
            {
                "title": "삼성전자 <b>뉴스</b>",
                "link": "https://news.example.com/1",
                "originallink": "https://news.example.com/1",
                "description": "삼성전자가 ...",
                "pubDate": "Mon, 16 Mar 2026 08:30:00 +0900"
            }
        ]
    }
    mock_response.raise_for_status = MagicMock()
    mocker.patch("requests.get", return_value=mock_response)

    client = NaverNewsClient(client_id="test_id", client_secret="test_secret")
    run_date = datetime(2026, 3, 16, 10, 0, 0, tzinfo=KST)
    articles = client.fetch_articles("삼성전자", max_count=10, run_date=run_date)

    assert len(articles) == 1
    assert articles[0]["title"] == "삼성전자 뉴스"
    assert articles[0]["url"] == "https://news.example.com/1"
    assert articles[0]["description"] == "삼성전자가 ..."

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
