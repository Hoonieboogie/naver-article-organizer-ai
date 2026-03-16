from unittest.mock import MagicMock
from src.summarizer import Summarizer


def test_summarize_returns_text(mocker):
    mock_client = MagicMock()
    mock_response = MagicMock()
    mock_response.text = "삼성전자는 3나노 공정 양산을 시작했으며..."
    mock_client.models.generate_content.return_value = mock_response
    mocker.patch("src.summarizer.genai.Client", return_value=mock_client)

    summarizer = Summarizer(api_key="fake")
    result = summarizer.summarize(title="삼성전자 3나노", content="원문 내용...")

    assert "삼성전자" in result
    assert isinstance(result, str)


def test_summarize_uses_correct_prompt(mocker):
    mock_client = MagicMock()
    mock_response = MagicMock()
    mock_response.text = "요약 결과"
    mock_client.models.generate_content.return_value = mock_response
    mocker.patch("src.summarizer.genai.Client", return_value=mock_client)

    summarizer = Summarizer(api_key="fake")
    summarizer.summarize(title="제목", content="본문 내용")

    call_args = mock_client.models.generate_content.call_args
    prompt = call_args.kwargs.get("contents") or call_args.args[1]
    assert "제목" in prompt
    assert "본문 내용" in prompt


def test_summarize_respects_rate_limit_delay(mocker):
    mock_client = MagicMock()
    mock_response = MagicMock()
    mock_response.text = "요약"
    mock_client.models.generate_content.return_value = mock_response
    mocker.patch("src.summarizer.genai.Client", return_value=mock_client)
    mock_sleep = mocker.patch("src.summarizer.time.sleep")

    summarizer = Summarizer(api_key="fake")
    summarizer.summarize(title="제목1", content="본문1")
    summarizer.summarize(title="제목2", content="본문2")

    mock_sleep.assert_called_with(6)
