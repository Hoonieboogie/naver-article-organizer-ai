from unittest.mock import MagicMock
from src.article_fetcher import ArticleFetcher, FetchResult


def test_fetch_returns_url_context_on_success(mocker):
    mock_response = MagicMock()
    mock_response.text = "기사 본문 내용입니다. " * 5  # 길이 충분히
    mocker.patch(
        "src.article_fetcher.ArticleFetcher._fetch_via_url_context",
        return_value=mock_response.text
    )

    fetcher = ArticleFetcher(gemini_api_key="fake_key")
    result = fetcher.fetch("https://example.com/article")

    assert isinstance(result, FetchResult)
    assert result.source == "url_context"
    assert "기사 본문" in result.content


def test_fetch_falls_back_to_bs4_when_gemini_fails(mocker):
    mocker.patch(
        "src.article_fetcher.ArticleFetcher._fetch_via_url_context",
        side_effect=Exception("Gemini failed")
    )
    mocker.patch(
        "src.article_fetcher.ArticleFetcher._fetch_via_bs4",
        return_value="BS4로 추출한 본문 내용입니다."
    )

    fetcher = ArticleFetcher(gemini_api_key="fake_key")
    result = fetcher.fetch("https://example.com/article")

    assert result.source == "bs4"
    assert "BS4로 추출한 본문" in result.content


def test_fetch_falls_back_to_description_when_bs4_fails(mocker):
    mocker.patch(
        "src.article_fetcher.ArticleFetcher._fetch_via_url_context",
        side_effect=Exception("Gemini failed")
    )
    mocker.patch(
        "src.article_fetcher.ArticleFetcher._fetch_via_bs4",
        side_effect=Exception("BS4 failed")
    )

    fetcher = ArticleFetcher(gemini_api_key="fake_key")
    result = fetcher.fetch("https://example.com/article", fallback_description="발췌문 내용")

    assert result.source == "description"
    assert result.content == "발췌문 내용"


def test_fetch_result_has_is_shallow_flag():
    result_url_context = FetchResult(content="본문", source="url_context")
    result_description = FetchResult(content="발췌문", source="description")

    assert result_url_context.is_shallow is False
    assert result_description.is_shallow is True
