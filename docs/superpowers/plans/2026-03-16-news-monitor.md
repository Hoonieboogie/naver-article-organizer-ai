# 네이버 뉴스 모니터 Implementation Plan

> **For agentic workers:** REQUIRED: Use superpowers:subagent-driven-development (if subagents available) or superpowers:executing-plans to implement this plan. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** 키워드별 네이버 뉴스를 매일 수집·요약하고 GitHub Pages 웹 UI에 표시하는 시스템 구축

**Architecture:** GitHub Actions(cron + workflow_dispatch)가 Python 스크립트를 실행해 네이버 API로 기사를 수집하고 Gemini로 요약한 뒤 날짜별 JSON을 docs/data/에 커밋한다. GitHub Pages의 SPA(index.html)가 JSON을 fetch해 렌더링하며, 웹 UI에서 GitHub API를 통해 config.json을 직접 수정한다.

**Tech Stack:** Python 3.11, pytest, google-genai SDK, requests, BeautifulSoup4, Vanilla JS (no framework), GitHub Actions, GitHub Pages

---

## File Structure

```
repo/
├── .github/workflows/daily.yml     # cron(01:00 UTC) + workflow_dispatch 트리거
├── src/
│   ├── naver_api.py                # 네이버 뉴스 검색 API 클라이언트
│   ├── article_fetcher.py          # 기사 원문 3단계 fallback 수집
│   ├── summarizer.py               # Gemini 2.5 Flash 요약
│   └── output_writer.py            # docs/data/{date}.json 저장
├── tests/
│   ├── test_naver_api.py
│   ├── test_article_fetcher.py
│   ├── test_summarizer.py
│   └── test_output_writer.py
├── run.py                          # 메인 오케스트레이션
├── config.json                     # 키워드·설정
├── requirements.txt
├── .gitignore
└── docs/
    ├── index.html                  # SPA 프론트엔드 (전체 UI)
    └── data/                       # 날짜별 JSON 결과 (GitHub Pages 서빙)
```

---

## Chunk 1: Project Scaffold

### Task 1: 기본 파일 구조 생성

**Files:**
- Create: `.gitignore`
- Create: `requirements.txt`
- Create: `config.json`
- Create: `src/__init__.py`
- Create: `tests/__init__.py`
- Create: `docs/data/.gitkeep`

- [ ] **Step 1: 디렉토리 및 기본 파일 생성**

```bash
mkdir -p src tests docs/data
touch src/__init__.py tests/__init__.py docs/data/.gitkeep
```

- [ ] **Step 2: `.gitignore` 작성**

```
# Python
__pycache__/
*.py[cod]
.venv/
*.env
.env

# 브라우저 세션 (비주얼 컴패니언)
.superpowers/
```

- [ ] **Step 3: `requirements.txt` 작성**

```
google-genai>=1.0.0
requests>=2.31.0
beautifulsoup4>=4.12.0
lxml>=5.0.0
pytest>=8.0.0
pytest-mock>=3.12.0
python-dateutil>=2.9.0
```

- [ ] **Step 4: `config.json` 작성**

```json
{
  "keywords": ["삼성전자"],
  "articles_per_keyword": 10,
  "schedule": "0 1 * * *"
}
```

- [ ] **Step 5: 커밋**

```bash
git add .gitignore requirements.txt config.json src/__init__.py tests/__init__.py docs/data/.gitkeep
git commit -m "chore: initial project scaffold"
```

---

### Task 2: GitHub Actions 워크플로우

**Files:**
- Create: `.github/workflows/daily.yml`

- [ ] **Step 1: 워크플로우 디렉토리 생성**

```bash
mkdir -p .github/workflows
```

- [ ] **Step 2: `daily.yml` 작성**

```yaml
name: Daily News Monitor

on:
  schedule:
    - cron: '0 1 * * *'   # 매일 10:00 KST (UTC 01:00)
  workflow_dispatch:        # 웹 UI "실행" 버튼에서 수동 트리거

jobs:
  run:
    runs-on: ubuntu-latest
    permissions:
      contents: write       # docs/data/ JSON 커밋을 위해 필요

    steps:
      - name: Checkout
        uses: actions/checkout@v4

      - name: Set up Python
        uses: actions/setup-python@v5
        with:
          python-version: '3.11'

      - name: Install dependencies
        run: pip install -r requirements.txt

      - name: Run news monitor
        env:
          NAVER_CLIENT_ID: ${{ secrets.NAVER_CLIENT_ID }}
          NAVER_CLIENT_SECRET: ${{ secrets.NAVER_CLIENT_SECRET }}
          GEMINI_API_KEY: ${{ secrets.GEMINI_API_KEY }}
        run: python run.py

      - name: Commit results
        run: |
          git config user.name "github-actions[bot]"
          git config user.email "github-actions[bot]@users.noreply.github.com"
          git add docs/data/
          git diff --staged --quiet || git commit -m "data: add news results $(date +%Y-%m-%d)"
          git push
```

- [ ] **Step 3: 커밋**

```bash
git add .github/workflows/daily.yml
git commit -m "ci: add GitHub Actions workflow for daily news collection"
```

---

### Task 3: GitHub Pages 설정

**Files:**
- Create: `docs/index.html` (빈 플레이스홀더 — Chunk 3에서 완성)

- [ ] **Step 1: 플레이스홀더 index.html 생성**

```html
<!DOCTYPE html>
<html lang="ko">
<head><meta charset="UTF-8"><title>뉴스 모니터</title></head>
<body><p>준비 중...</p></body>
</html>
```

- [ ] **Step 2: 커밋 후 GitHub에 push**

```bash
git add docs/index.html
git commit -m "docs: add placeholder index.html for GitHub Pages"
git push
```

  > GitHub 레포 Settings → Pages → Source: `main` 브랜치 `/docs` 폴더로 설정

- [ ] **Step 3: GitHub Secrets 등록 확인**

  GitHub 레포 → Settings → Secrets and variables → Actions에 다음 4개 등록:
  - `NAVER_CLIENT_ID`
  - `NAVER_CLIENT_SECRET`
  - `GEMINI_API_KEY`
  - `GH_TOKEN` (웹 UI에서 config.json 수정용 — 레포 write 권한 필요한 PAT)

---

## Chunk 2: Backend Pipeline

### Task 4: Naver API 클라이언트 (`src/naver_api.py`)

**Files:**
- Create: `src/naver_api.py`
- Create: `tests/test_naver_api.py`

네이버 뉴스 검색 API를 호출해 기사 목록을 반환한다. 기간 필터(전날 10:00 KST ~ 당일 09:00 KST)를 적용한다.

- [ ] **Step 1: 실패하는 테스트 작성**

`tests/test_naver_api.py`:
```python
from unittest.mock import patch, MagicMock
from datetime import datetime, timezone, timedelta
from src.naver_api import NaverNewsClient, parse_pub_date, is_in_window

KST = timezone(timedelta(hours=9))

def test_parse_pub_date_returns_aware_datetime():
    # 네이버 API는 RFC 822 형식으로 날짜를 반환한다
    raw = "Mon, 16 Mar 2026 08:30:00 +0900"
    result = parse_pub_date(raw)
    assert result.tzinfo is not None
    assert result.year == 2026
    assert result.month == 3
    assert result.day == 16
    assert result.hour == 8

def test_is_in_window_includes_article_in_range():
    # 수집 윈도우: 전날 10:00 KST ~ 당일 09:00 KST
    run_date = datetime(2026, 3, 16, 10, 0, 0, tzinfo=KST)
    article_dt = datetime(2026, 3, 16, 8, 0, 0, tzinfo=KST)
    assert is_in_window(article_dt, run_date) is True

def test_is_in_window_excludes_article_before_window():
    run_date = datetime(2026, 3, 16, 10, 0, 0, tzinfo=KST)
    article_dt = datetime(2026, 3, 15, 9, 0, 0, tzinfo=KST)  # 전날 09:00 — 윈도우 전
    assert is_in_window(article_dt, run_date) is False

def test_is_in_window_excludes_article_after_window():
    run_date = datetime(2026, 3, 16, 10, 0, 0, tzinfo=KST)
    article_dt = datetime(2026, 3, 16, 9, 30, 0, tzinfo=KST)  # 당일 09:30 — 윈도우 후
    assert is_in_window(article_dt, run_date) is False

def test_fetch_articles_calls_naver_api(mocker):
    mock_response = MagicMock()
    mock_response.json.return_value = {
        "items": [
            {
                "title": "삼성전자 <b>뉴스</b>",
                "link": "https://news.example.com/1",
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
    assert articles[0]["title"] == "삼성전자 뉴스"   # HTML 태그 제거됨
    assert articles[0]["url"] == "https://news.example.com/1"
    assert articles[0]["description"] == "삼성전자가 ..."

def test_fetch_articles_filters_out_of_window(mocker):
    mock_response = MagicMock()
    mock_response.json.return_value = {
        "items": [
            {
                "title": "오래된 기사",
                "link": "https://news.example.com/2",
                "description": "...",
                "pubDate": "Sat, 14 Mar 2026 08:00:00 +0900"  # 윈도우 밖
            }
        ]
    }
    mock_response.raise_for_status = MagicMock()
    mocker.patch("requests.get", return_value=mock_response)

    client = NaverNewsClient(client_id="test_id", client_secret="test_secret")
    run_date = datetime(2026, 3, 16, 10, 0, 0, tzinfo=KST)
    articles = client.fetch_articles("삼성전자", max_count=10, run_date=run_date)

    assert len(articles) == 0
```

- [ ] **Step 2: 테스트 실행 — 실패 확인**

```bash
pytest tests/test_naver_api.py -v
```
Expected: `ModuleNotFoundError` or `ImportError`

- [ ] **Step 3: `src/naver_api.py` 구현**

```python
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
    수집 윈도우 확인: 전날 10:00 KST ~ 당일 09:00 KST
    run_date: 실행 시각 (당일 10:00 KST 기준)
    """
    run_date_kst = run_date.astimezone(KST)
    today = run_date_kst.date()
    yesterday = today - timedelta(days=1)

    window_start = datetime(yesterday.year, yesterday.month, yesterday.day, 10, 0, 0, tzinfo=KST)
    window_end   = datetime(today.year,     today.month,     today.day,     9, 0, 0, tzinfo=KST)

    return window_start <= article_dt < window_end


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
```

- [ ] **Step 4: 테스트 실행 — 통과 확인**

```bash
pytest tests/test_naver_api.py -v
```
Expected: 5 tests PASSED

- [ ] **Step 5: 커밋**

```bash
git add src/naver_api.py tests/test_naver_api.py
git commit -m "feat: add Naver News API client with date window filtering"
```

---

### Task 5: 기사 원문 수집 — 3단계 Fallback (`src/article_fetcher.py`)

**Files:**
- Create: `src/article_fetcher.py`
- Create: `tests/test_article_fetcher.py`

- [ ] **Step 1: 실패하는 테스트 작성**

`tests/test_article_fetcher.py`:
```python
from unittest.mock import patch, MagicMock
from src.article_fetcher import ArticleFetcher, FetchResult

def test_fetch_returns_url_context_on_success(mocker):
    mock_model = MagicMock()
    mock_response = MagicMock()
    mock_response.text = "기사 본문 내용입니다."
    mock_model.generate_content.return_value = mock_response
    mocker.patch("src.article_fetcher.genai.Client", return_value=MagicMock(
        models=MagicMock(generate_content=MagicMock(return_value=mock_response))
    ))

    fetcher = ArticleFetcher(gemini_api_key="fake_key")
    result = fetcher.fetch("https://example.com/article")

    assert isinstance(result, FetchResult)
    assert result.source == "url_context"
    assert result.content == "기사 본문 내용입니다."

def test_fetch_falls_back_to_bs4_when_gemini_fails(mocker):
    # Gemini url_context 실패 시뮬레이션
    mocker.patch("src.article_fetcher.ArticleFetcher._fetch_via_url_context",
                 side_effect=Exception("Gemini failed"))

    html = "<html><body><article><p>BS4로 추출한 본문</p></article></body></html>"
    mock_resp = MagicMock()
    mock_resp.text = html
    mock_resp.raise_for_status = MagicMock()
    mocker.patch("requests.get", return_value=mock_resp)

    fetcher = ArticleFetcher(gemini_api_key="fake_key")
    result = fetcher.fetch("https://example.com/article")

    assert result.source == "bs4"
    assert "BS4로 추출한 본문" in result.content

def test_fetch_falls_back_to_description_when_bs4_fails(mocker):
    mocker.patch("src.article_fetcher.ArticleFetcher._fetch_via_url_context",
                 side_effect=Exception("Gemini failed"))
    mocker.patch("src.article_fetcher.ArticleFetcher._fetch_via_bs4",
                 side_effect=Exception("BS4 failed"))

    fetcher = ArticleFetcher(gemini_api_key="fake_key")
    result = fetcher.fetch("https://example.com/article", fallback_description="발췌문 내용")

    assert result.source == "description"
    assert result.content == "발췌문 내용"

def test_fetch_result_has_is_shallow_flag():
    result_url_context = FetchResult(content="본문", source="url_context")
    result_description = FetchResult(content="발췌문", source="description")

    assert result_url_context.is_shallow is False
    assert result_description.is_shallow is True
```

- [ ] **Step 2: 테스트 실행 — 실패 확인**

```bash
pytest tests/test_article_fetcher.py -v
```
Expected: `ImportError`

- [ ] **Step 3: `src/article_fetcher.py` 구현**

```python
from dataclasses import dataclass, field
from typing import Optional
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
```

- [ ] **Step 4: 테스트 실행 — 통과 확인**

```bash
pytest tests/test_article_fetcher.py -v
```
Expected: 4 tests PASSED

- [ ] **Step 5: 커밋**

```bash
git add src/article_fetcher.py tests/test_article_fetcher.py
git commit -m "feat: add article fetcher with 3-step fallback (url_context/bs4/description)"
```

---

### Task 6: Gemini 요약 (`src/summarizer.py`)

**Files:**
- Create: `src/summarizer.py`
- Create: `tests/test_summarizer.py`

- [ ] **Step 1: 실패하는 테스트 작성**

`tests/test_summarizer.py`:
```python
import time
from unittest.mock import MagicMock, call, patch
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

    # 두 번째 호출 시 딜레이 적용
    mock_sleep.assert_called_with(6)
```

- [ ] **Step 2: 테스트 실행 — 실패 확인**

```bash
pytest tests/test_summarizer.py -v
```
Expected: `ImportError`

- [ ] **Step 3: `src/summarizer.py` 구현**

```python
import time
from google import genai

PROMPT_TEMPLATE = """다음 기사를 요약해줘.

규칙:
1. 반드시 기사에 등장한 단어만 사용할 것
2. 핵심 내용을 빠짐없이 포함할 것
3. 중요한 수치, 인물, 사건이 있으면 반드시 포함할 것
4. 길이 제한 없음 — 필요한 만큼 써도 됨

기사 제목: {title}

기사 본문:
{content}

요약:"""


class Summarizer:
    MODEL = "gemini-2.5-flash"

    def __init__(self, api_key: str):
        self._client = genai.Client(api_key=api_key)
        self._call_count = 0

    def summarize(self, title: str, content: str) -> str:
        """기사 제목과 본문을 받아 요약문을 반환한다. 분당 10회 제한 준수."""
        if self._call_count > 0:
            time.sleep(6)  # 분당 10회 = 6초 간격

        prompt = PROMPT_TEMPLATE.format(title=title, content=content[:8000])  # 토큰 절약
        response = self._client.models.generate_content(
            model=self.MODEL,
            contents=prompt,
        )
        self._call_count += 1
        return response.text.strip()
```

- [ ] **Step 4: 테스트 실행 — 통과 확인**

```bash
pytest tests/test_summarizer.py -v
```
Expected: 3 tests PASSED

- [ ] **Step 5: 커밋**

```bash
git add src/summarizer.py tests/test_summarizer.py
git commit -m "feat: add Gemini summarizer with rate limit enforcement"
```

---

### Task 7: JSON 출력 (`src/output_writer.py`)

**Files:**
- Create: `src/output_writer.py`
- Create: `tests/test_output_writer.py`

- [ ] **Step 1: 실패하는 테스트 작성**

`tests/test_output_writer.py`:
```python
import json
import os
import tempfile
from datetime import datetime, timezone, timedelta
from src.output_writer import OutputWriter

KST = timezone(timedelta(hours=9))

def test_write_creates_json_file():
    with tempfile.TemporaryDirectory() as tmpdir:
        writer = OutputWriter(output_dir=tmpdir)
        run_date = datetime(2026, 3, 16, 10, 0, 0, tzinfo=KST)
        data = [
            {
                "keyword": "삼성전자",
                "articles": [
                    {
                        "title": "삼성전자 뉴스",
                        "url": "https://example.com/1",
                        "published_at": "2026-03-16T08:30:00+09:00",
                        "summary": "요약 내용",
                        "source": "url_context",
                    }
                ],
            }
        ]
        path = writer.write(run_date=run_date, keyword_results=data)

        assert os.path.exists(path)
        assert "2026-03-16" in path

def test_write_json_structure():
    with tempfile.TemporaryDirectory() as tmpdir:
        writer = OutputWriter(output_dir=tmpdir)
        run_date = datetime(2026, 3, 16, 10, 5, 32, tzinfo=KST)
        data = []
        path = writer.write(run_date=run_date, keyword_results=data)

        with open(path) as f:
            result = json.load(f)

        assert result["date"] == "2026-03-16"
        assert "generated_at" in result
        assert result["keywords"] == []
```

- [ ] **Step 2: 테스트 실행 — 실패 확인**

```bash
pytest tests/test_output_writer.py -v
```
Expected: `ImportError`

- [ ] **Step 3: `src/output_writer.py` 구현**

```python
import json
import os
from datetime import datetime


class OutputWriter:
    def __init__(self, output_dir: str = "docs/data"):
        self.output_dir = output_dir
        os.makedirs(output_dir, exist_ok=True)

    def write(self, run_date: datetime, keyword_results: list[dict]) -> str:
        """날짜별 JSON 파일을 docs/data/{YYYY-MM-DD}.json 에 저장한다."""
        date_str = run_date.strftime("%Y-%m-%d")
        payload = {
            "date": date_str,
            "generated_at": run_date.isoformat(),
            "keywords": keyword_results,
        }
        path = os.path.join(self.output_dir, f"{date_str}.json")
        with open(path, "w", encoding="utf-8") as f:
            json.dump(payload, f, ensure_ascii=False, indent=2)
        return path
```

- [ ] **Step 4: 테스트 실행 — 통과 확인**

```bash
pytest tests/test_output_writer.py -v
```
Expected: 2 tests PASSED

- [ ] **Step 5: 커밋**

```bash
git add src/output_writer.py tests/test_output_writer.py
git commit -m "feat: add output writer for date-indexed JSON results"
```

---

### Task 8: 메인 오케스트레이션 (`run.py`)

**Files:**
- Create: `run.py`

- [ ] **Step 1: `run.py` 작성**

```python
"""
네이버 뉴스 모니터 메인 실행 스크립트.
환경 변수: NAVER_CLIENT_ID, NAVER_CLIENT_SECRET, GEMINI_API_KEY
"""
import os
import sys
import json
from datetime import datetime, timezone, timedelta

from src.naver_api import NaverNewsClient
from src.article_fetcher import ArticleFetcher
from src.summarizer import Summarizer
from src.output_writer import OutputWriter

KST = timezone(timedelta(hours=9))


def load_config(path: str = "config.json") -> dict:
    with open(path, encoding="utf-8") as f:
        return json.load(f)


def main():
    # 환경 변수 확인
    naver_id = os.environ["NAVER_CLIENT_ID"]
    naver_secret = os.environ["NAVER_CLIENT_SECRET"]
    gemini_key = os.environ["GEMINI_API_KEY"]

    config = load_config()
    keywords = config.get("keywords", [])
    articles_per_keyword = config.get("articles_per_keyword", 10)

    if not keywords:
        print("config.json에 키워드가 없습니다. 종료합니다.")
        sys.exit(0)

    run_date = datetime.now(tz=KST)
    print(f"실행 시작: {run_date.isoformat()}")
    print(f"키워드: {keywords} / 키워드당 기사 수: {articles_per_keyword}")

    naver = NaverNewsClient(client_id=naver_id, client_secret=naver_secret)
    fetcher = ArticleFetcher(gemini_api_key=gemini_key)
    summarizer = Summarizer(api_key=gemini_key)
    writer = OutputWriter()

    keyword_results = []

    for keyword in keywords:
        print(f"\n[{keyword}] 기사 수집 중...")
        articles_meta = naver.fetch_articles(keyword, max_count=articles_per_keyword, run_date=run_date)
        print(f"  → {len(articles_meta)}개 기사 발견")

        articles_output = []
        for i, meta in enumerate(articles_meta, 1):
            print(f"  [{i}/{len(articles_meta)}] {meta['title'][:40]}...")

            fetch_result = fetcher.fetch(meta["url"], fallback_description=meta["description"])
            print(f"    수집 방법: {fetch_result.source}")

            summary = summarizer.summarize(title=meta["title"], content=fetch_result.content)
            print(f"    요약 완료 ({len(summary)}자)")

            articles_output.append({
                "title": meta["title"],
                "url": meta["url"],
                "published_at": meta["published_at"],
                "summary": summary,
                "source": fetch_result.source,
            })

        keyword_results.append({"keyword": keyword, "articles": articles_output})

    output_path = writer.write(run_date=run_date, keyword_results=keyword_results)
    print(f"\n✅ 완료: {output_path}")


if __name__ == "__main__":
    main()
```

- [ ] **Step 2: 로컬에서 구문 오류 확인**

```bash
python -m py_compile run.py && echo "OK"
```
Expected: `OK`

- [ ] **Step 3: 전체 테스트 실행**

```bash
pytest tests/ -v
```
Expected: 모든 테스트 PASSED

- [ ] **Step 4: 커밋**

```bash
git add run.py
git commit -m "feat: add main orchestration script"
```

---

## Chunk 3: Frontend SPA

### Task 9: 웹 UI (`docs/index.html`)

**Files:**
- Modify: `docs/index.html` (Chunk 1에서 만든 플레이스홀더 교체)

단일 HTML 파일 SPA. 외부 의존성 없음(Vanilla JS + CSS). 기능:
- GitHub PAT 모달 (초기 설정)
- 사이드바: 키워드 목록 / 추가·삭제 / 기사 수 설정 / 날짜 선택 / 실행 버튼 / 설정 버튼
- 메인 패널: 기사 카드 (체크박스, 제목, 요약, 링크, 메타정보, ⚠️ 표시)
- 복사 버튼: 선택 기사 URL을 지정 포맷으로 클립보드 복사
- 실행 버튼: workflow_dispatch 호출 + 5초 폴링 + 완료 시 자동 로드

- [ ] **Step 1: `docs/index.html` 전체 작성**

```html
<!DOCTYPE html>
<html lang="ko">
<head>
  <meta charset="UTF-8">
  <meta name="viewport" content="width=device-width, initial-scale=1.0">
  <title>뉴스 모니터</title>
  <style>
    *, *::before, *::after { box-sizing: border-box; margin: 0; padding: 0; }

    body {
      font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", sans-serif;
      background: #f5f6fa;
      color: #222;
      height: 100vh;
      display: flex;
      flex-direction: column;
    }

    /* ── 헤더 ── */
    header {
      background: #1a1a2e;
      color: white;
      padding: 12px 20px;
      display: flex;
      align-items: center;
      gap: 12px;
      flex-shrink: 0;
    }
    header h1 { font-size: 16px; font-weight: 600; }
    header .date-label { font-size: 12px; color: #aaa; margin-left: auto; }

    /* ── 메인 레이아웃 ── */
    .layout {
      display: flex;
      flex: 1;
      overflow: hidden;
    }

    /* ── 사이드바 ── */
    .sidebar {
      width: 220px;
      background: #f0f2f5;
      border-right: 1px solid #ddd;
      display: flex;
      flex-direction: column;
      padding: 16px 12px;
      gap: 12px;
      overflow-y: auto;
      flex-shrink: 0;
    }
    .sidebar-section { display: flex; flex-direction: column; gap: 6px; }
    .sidebar-label {
      font-size: 10px; font-weight: 700; letter-spacing: 1px;
      text-transform: uppercase; color: #888;
    }
    .keyword-item {
      display: flex; align-items: center; gap: 6px;
      background: white; border: 1px solid #e0e0e0; border-radius: 6px;
      padding: 7px 10px; cursor: pointer; font-size: 13px;
      transition: border-color .15s;
    }
    .keyword-item:hover { border-color: #4285f4; }
    .keyword-item.active { border-color: #4285f4; background: #e8f0fe; color: #1a73e8; font-weight: 600; }
    .keyword-item .badge {
      margin-left: auto; background: #eee; border-radius: 10px;
      padding: 1px 6px; font-size: 10px; color: #666;
    }
    .keyword-item.active .badge { background: #c8dcfc; color: #1a73e8; }
    .keyword-item .del-btn {
      margin-left: 4px; color: #bbb; font-size: 14px; line-height: 1;
      cursor: pointer; flex-shrink: 0;
    }
    .keyword-item .del-btn:hover { color: #e53935; }

    .add-keyword-row {
      display: flex; gap: 4px;
    }
    .add-keyword-row input {
      flex: 1; padding: 6px 8px; border: 1px solid #ddd; border-radius: 4px;
      font-size: 12px; outline: none;
    }
    .add-keyword-row input:focus { border-color: #4285f4; }
    .add-keyword-row button {
      padding: 6px 10px; background: #4285f4; color: white; border: none;
      border-radius: 4px; font-size: 12px; cursor: pointer;
    }

    .sidebar-input-row {
      display: flex; align-items: center; gap: 8px; font-size: 12px; color: #555;
    }
    .sidebar-input-row input[type=number] {
      width: 52px; padding: 4px 6px; border: 1px solid #ddd; border-radius: 4px;
      font-size: 12px; text-align: center;
    }

    select.date-select {
      width: 100%; padding: 6px 8px; border: 1px solid #ddd; border-radius: 4px;
      font-size: 12px; background: white; cursor: pointer;
    }

    .run-btn {
      width: 100%; padding: 10px; background: #34a853; color: white;
      border: none; border-radius: 6px; font-size: 13px; font-weight: 600;
      cursor: pointer; display: flex; align-items: center; justify-content: center; gap: 6px;
      transition: background .15s;
    }
    .run-btn:disabled { background: #aaa; cursor: not-allowed; }
    .run-btn:not(:disabled):hover { background: #2d924a; }
    .run-hint { font-size: 10px; color: #999; text-align: center; }

    .settings-btn {
      width: 100%; padding: 7px; background: white; color: #666;
      border: 1px solid #ddd; border-radius: 6px; font-size: 12px; cursor: pointer;
    }
    .settings-btn:hover { border-color: #aaa; }

    /* ── 메인 패널 ── */
    .main {
      flex: 1; overflow-y: auto; padding: 20px;
    }

    .main-header {
      display: flex; align-items: center; justify-content: space-between;
      margin-bottom: 14px;
    }
    .main-header h2 { font-size: 18px; font-weight: 700; }
    .main-header .meta { font-size: 12px; color: #999; margin-left: 10px; }

    .copy-btn {
      padding: 7px 14px; background: white; border: 1px solid #ddd;
      border-radius: 6px; font-size: 12px; cursor: pointer; white-space: nowrap;
    }
    .copy-btn:not(:disabled):hover { border-color: #4285f4; color: #4285f4; }
    .copy-btn:disabled { color: #bbb; cursor: not-allowed; }

    .article-card {
      background: white; border: 1px solid #e0e0e0; border-radius: 8px;
      padding: 14px; margin-bottom: 10px; display: flex; gap: 12px;
      transition: border-color .15s;
    }
    .article-card:hover { border-color: #c0c0c0; }
    .article-card.checked { border-color: #4285f4; background: #fafcff; }
    .article-card.shallow { background: #fffbf0; border-color: #ffe082; }

    .article-card input[type=checkbox] {
      margin-top: 2px; flex-shrink: 0; width: 16px; height: 16px; cursor: pointer;
    }
    .article-body { flex: 1; }
    .article-title {
      font-size: 14px; font-weight: 600; margin-bottom: 6px; line-height: 1.4;
    }
    .article-title a {
      color: #222; text-decoration: none; margin-left: 6px;
      font-size: 12px; color: #4285f4;
    }
    .article-title a:hover { text-decoration: underline; }
    .article-summary { font-size: 13px; color: #444; line-height: 1.6; margin-bottom: 8px; }
    .article-meta { font-size: 11px; color: #aaa; }
    .shallow-badge {
      display: inline-block; background: #fff3cd; color: #856404;
      padding: 1px 6px; border-radius: 4px; font-size: 10px; margin-right: 4px;
    }

    .empty-state {
      text-align: center; color: #aaa; padding: 60px 20px; font-size: 14px;
    }

    /* ── 모달 ── */
    .modal-overlay {
      position: fixed; inset: 0; background: rgba(0,0,0,.5);
      display: flex; align-items: center; justify-content: center; z-index: 100;
    }
    .modal-overlay.hidden { display: none; }
    .modal {
      background: white; border-radius: 10px; padding: 28px; width: 400px;
      max-width: 90vw; box-shadow: 0 8px 32px rgba(0,0,0,.2);
    }
    .modal h3 { font-size: 16px; margin-bottom: 8px; }
    .modal p { font-size: 13px; color: #555; margin-bottom: 16px; line-height: 1.5; }
    .modal input[type=text] {
      width: 100%; padding: 9px 12px; border: 1px solid #ddd; border-radius: 6px;
      font-size: 13px; margin-bottom: 12px; outline: none; font-family: monospace;
    }
    .modal input:focus { border-color: #4285f4; }
    .modal-actions { display: flex; gap: 8px; justify-content: flex-end; }
    .modal-actions button {
      padding: 8px 18px; border-radius: 6px; font-size: 13px; cursor: pointer; border: none;
    }
    .btn-primary { background: #4285f4; color: white; }
    .btn-secondary { background: #eee; color: #333; }

    /* ── 스피너 ── */
    .spinner {
      width: 14px; height: 14px; border: 2px solid rgba(255,255,255,.4);
      border-top-color: white; border-radius: 50%;
      animation: spin .6s linear infinite;
    }
    @keyframes spin { to { transform: rotate(360deg); } }

    /* ── 토스트 ── */
    .toast {
      position: fixed; bottom: 24px; left: 50%; transform: translateX(-50%);
      background: #333; color: white; padding: 10px 20px; border-radius: 20px;
      font-size: 13px; opacity: 0; transition: opacity .3s; pointer-events: none; z-index: 200;
    }
    .toast.show { opacity: 1; }
  </style>
</head>
<body>

<!-- 헤더 -->
<header>
  <span>📰</span>
  <h1>뉴스 모니터</h1>
  <span class="date-label" id="headerDate"></span>
</header>

<!-- 메인 레이아웃 -->
<div class="layout">

  <!-- 사이드바 -->
  <aside class="sidebar">

    <div class="sidebar-section">
      <div class="sidebar-label">키워드</div>
      <div id="keywordList"></div>
      <div class="add-keyword-row">
        <input type="text" id="newKeywordInput" placeholder="키워드 추가...">
        <button onclick="addKeyword()">+</button>
      </div>
    </div>

    <div class="sidebar-section">
      <div class="sidebar-label">기사 수</div>
      <div class="sidebar-input-row">
        <input type="number" id="articlesPerKeyword" min="1" max="20" value="10"
               onchange="saveArticlesPerKeyword()">
        <span>개 / 키워드</span>
      </div>
    </div>

    <div class="sidebar-section">
      <div class="sidebar-label">날짜</div>
      <select class="date-select" id="dateSelect" onchange="loadDate(this.value)"></select>
    </div>

    <div class="sidebar-section" style="margin-top:auto;">
      <button class="run-btn" id="runBtn" onclick="runWorkflow()">
        ▶ 실행
      </button>
      <div class="run-hint" id="runHint">약 15~20분 소요</div>
      <button class="settings-btn" onclick="openSettings()">⚙️ GitHub 설정</button>
    </div>

  </aside>

  <!-- 메인 패널 -->
  <main class="main" id="mainPanel">
    <div class="empty-state">키워드를 선택하거나 실행해 주세요.</div>
  </main>

</div>

<!-- PAT 모달 -->
<div class="modal-overlay" id="patModal">
  <div class="modal">
    <h3>🔑 GitHub 설정</h3>
    <p>
      키워드 관리 및 실행 기능을 사용하려면 GitHub Personal Access Token이 필요합니다.<br>
      레포지토리 <code>read/write</code> 권한이 포함된 PAT를 입력해주세요.
    </p>
    <input type="text" id="patInput" placeholder="ghp_xxxxxxxxxxxx">
    <input type="text" id="repoInput" placeholder="owner/repo-name (예: johndoe/news-monitor)">
    <div class="modal-actions">
      <button class="btn-secondary" onclick="closePatModal()">나중에</button>
      <button class="btn-primary" onclick="savePat()">저장</button>
    </div>
  </div>
</div>

<!-- 토스트 -->
<div class="toast" id="toast"></div>

<script>
  // ── 상태 ─────────────────────────────────────────────
  let config = { keywords: [], articles_per_keyword: 10 };
  let currentKeyword = null;
  let currentDate = null;
  let availableDates = [];
  let pollingInterval = null;

  const BASE_DATA_URL = "./data/";

  // ── 초기화 ──────────────────────────────────────────
  async function init() {
    updateHeaderDate();
    await loadConfig();
    await scanAvailableDates();
    checkPatModal();
  }

  function updateHeaderDate() {
    const now = new Date();
    document.getElementById("headerDate").textContent =
      now.toLocaleDateString("ko-KR", { year:"numeric", month:"long", day:"numeric" });
  }

  // ── config.json 로드 ─────────────────────────────────
  // config.json은 docs/ 밖(레포 루트)에 있어 GitHub Pages에서 직접 접근 불가.
  // PAT가 있으면 GitHub Contents API로 읽고, 없으면 빈 기본값을 사용한다.
  async function loadConfig() {
    const { token, repo } = getStoredPat();
    if (token && repo) {
      try {
        const res = await fetch(
          `https://api.github.com/repos/${repo}/contents/config.json`,
          { headers: { Authorization: `token ${token}`, Accept: "application/vnd.github.v3+json" } }
        );
        if (!res.ok) throw new Error();
        const meta = await res.json();
        // GitHub API는 Base64로 인코딩된 content를 반환한다
        config = JSON.parse(decodeURIComponent(escape(atob(meta.content))));
      } catch {
        config = { keywords: [], articles_per_keyword: 10 };
      }
    } else {
      config = { keywords: [], articles_per_keyword: 10 };
    }
    renderKeywordList();
    document.getElementById("articlesPerKeyword").value = config.articles_per_keyword || 10;
  }

  function renderKeywordList() {
    const list = document.getElementById("keywordList");
    list.innerHTML = "";
    (config.keywords || []).forEach(kw => {
      const el = document.createElement("div");
      el.className = "keyword-item" + (kw === currentKeyword ? " active" : "");
      el.innerHTML = `
        <span onclick="selectKeyword('${kw}')" style="flex:1;cursor:pointer">${kw}</span>
        <span class="badge" id="badge-${kw}">-</span>
        <span class="del-btn" onclick="removeKeyword('${kw}')">✕</span>
      `;
      list.appendChild(el);
    });
  }

  // ── 날짜 스캔 ────────────────────────────────────────
  async function scanAvailableDates() {
    // GitHub Pages에서는 디렉토리 목록을 직접 읽을 수 없으므로
    // 최근 30일간의 날짜를 시도해 존재 여부를 확인한다.
    availableDates = [];
    const today = new Date();
    const checks = [];
    for (let i = 0; i < 30; i++) {
      const d = new Date(today);
      d.setDate(d.getDate() - i);
      const dateStr = d.toISOString().slice(0, 10);
      checks.push(
        fetch(BASE_DATA_URL + dateStr + ".json", { method: "HEAD" })
          .then(r => r.ok ? dateStr : null)
          .catch(() => null)
      );
    }
    const results = await Promise.all(checks);
    availableDates = results.filter(Boolean).sort().reverse();
    renderDateSelect();

    if (availableDates.length > 0) {
      loadDate(availableDates[0]);
    }
  }

  function renderDateSelect() {
    const sel = document.getElementById("dateSelect");
    sel.innerHTML = "";
    if (availableDates.length === 0) {
      sel.innerHTML = '<option value="">결과 없음</option>';
      return;
    }
    availableDates.forEach((d, i) => {
      const opt = document.createElement("option");
      opt.value = d;
      opt.textContent = d + (i === 0 ? " (최신)" : "");
      sel.appendChild(opt);
    });
  }

  // ── 날짜 데이터 로드 ─────────────────────────────────
  async function loadDate(dateStr) {
    if (!dateStr) return;
    currentDate = dateStr;
    try {
      const res = await fetch(BASE_DATA_URL + dateStr + ".json?t=" + Date.now());
      if (!res.ok) throw new Error("not found");
      const data = await res.json();
      applyData(data);
    } catch {
      showEmptyState("선택한 날짜의 데이터를 불러올 수 없습니다.");
    }
  }

  function applyData(data) {
    // 뱃지 업데이트
    (data.keywords || []).forEach(kd => {
      const badge = document.getElementById("badge-" + kd.keyword);
      if (badge) badge.textContent = kd.articles.length;
    });

    // 현재 키워드가 없으면 첫 번째 키워드 선택
    if (!currentKeyword && data.keywords && data.keywords.length > 0) {
      selectKeyword(data.keywords[0].keyword, data);
    } else if (currentKeyword) {
      const kd = (data.keywords || []).find(k => k.keyword === currentKeyword);
      if (kd) renderArticles(kd, data.date);
    }

    window.__lastData = data;
  }

  // ── 키워드 선택 ──────────────────────────────────────
  function selectKeyword(kw, data) {
    currentKeyword = kw;
    renderKeywordList();

    const d = data || window.__lastData;
    if (!d) return;
    const kd = (d.keywords || []).find(k => k.keyword === kw);
    if (kd) renderArticles(kd, d.date);
  }

  // ── 기사 렌더링 ──────────────────────────────────────
  function renderArticles(kwData, date) {
    const panel = document.getElementById("mainPanel");
    const articles = kwData.articles || [];

    if (articles.length === 0) {
      panel.innerHTML = `<div class="empty-state">수집된 기사가 없습니다.</div>`;
      return;
    }

    panel.innerHTML = `
      <div class="main-header">
        <div>
          <span style="font-size:18px;font-weight:700">${kwData.keyword}</span>
          <span class="meta">${date} · ${articles.length}개 기사</span>
        </div>
        <button class="copy-btn" id="copyBtn" onclick="copySelected()" disabled>📋 선택 항목 복사</button>
      </div>
      <div id="articleList"></div>
    `;

    const list = document.getElementById("articleList");
    articles.forEach((art, i) => {
      const isShallow = art.source === "description";
      const card = document.createElement("div");
      card.className = "article-card" + (isShallow ? " shallow" : "");
      card.id = "card-" + i;
      card.innerHTML = `
        <input type="checkbox" id="chk-${i}" onchange="onCheckChange()">
        <div class="article-body">
          <div class="article-title">
            ${art.title}
            <a href="${art.url}" target="_blank" rel="noopener">↗</a>
          </div>
          <div class="article-summary">${art.summary}</div>
          <div class="article-meta">
            ${isShallow ? '<span class="shallow-badge">⚠️ 발췌문 기반</span>' : ""}
            ${formatTime(art.published_at)} · ${art.source}
          </div>
        </div>
      `;
      list.appendChild(card);
    });
  }

  function formatTime(isoStr) {
    if (!isoStr) return "";
    try {
      return new Date(isoStr).toLocaleString("ko-KR", { month:"numeric", day:"numeric", hour:"2-digit", minute:"2-digit" });
    } catch { return isoStr; }
  }

  // ── 체크박스 ─────────────────────────────────────────
  function onCheckChange() {
    const anyChecked = document.querySelectorAll("#articleList input[type=checkbox]:checked").length > 0;
    const btn = document.getElementById("copyBtn");
    if (btn) btn.disabled = !anyChecked;

    document.querySelectorAll(".article-card").forEach((card, i) => {
      const chk = document.getElementById("chk-" + i);
      if (chk) card.classList.toggle("checked", chk.checked);
    });
  }

  // ── 복사 ─────────────────────────────────────────────
  function copySelected() {
    if (!currentKeyword || !window.__lastData) return;
    const kd = (window.__lastData.keywords || []).find(k => k.keyword === currentKeyword);
    if (!kd) return;

    const checked = document.querySelectorAll("#articleList input[type=checkbox]:checked");
    const indices = Array.from(checked).map(el => parseInt(el.id.replace("chk-", "")));
    const urls = indices.map(i => kd.articles[i]?.url).filter(Boolean);

    const text = currentKeyword + "\n" + urls.map(u => "* " + u).join("\n");
    navigator.clipboard.writeText(text).then(() => showToast("복사됨!"));
  }

  // ── 키워드 관리 ──────────────────────────────────────
  async function addKeyword() {
    const input = document.getElementById("newKeywordInput");
    const kw = input.value.trim();
    if (!kw || config.keywords.includes(kw)) return;
    config.keywords.push(kw);
    input.value = "";
    renderKeywordList();
    await saveConfig();
  }

  async function removeKeyword(kw) {
    config.keywords = config.keywords.filter(k => k !== kw);
    if (currentKeyword === kw) currentKeyword = null;
    renderKeywordList();
    await saveConfig();
  }

  async function saveArticlesPerKeyword() {
    const val = parseInt(document.getElementById("articlesPerKeyword").value);
    if (val < 1 || val > 20) return;
    config.articles_per_keyword = val;
    await saveConfig();
  }

  // ── GitHub API: config.json 저장 ─────────────────────
  async function saveConfig() {
    const { token, repo } = getStoredPat();
    if (!token || !repo) { showToast("GitHub 설정이 필요합니다."); return; }

    try {
      // 현재 파일의 SHA 가져오기 (업데이트에 필요)
      const metaRes = await fetch(`https://api.github.com/repos/${repo}/contents/config.json`, {
        headers: { Authorization: `token ${token}`, Accept: "application/vnd.github.v3+json" }
      });
      const meta = await metaRes.json();

      const content = btoa(unescape(encodeURIComponent(JSON.stringify(config, null, 2))));
      const res = await fetch(`https://api.github.com/repos/${repo}/contents/config.json`, {
        method: "PUT",
        headers: {
          Authorization: `token ${token}`,
          "Content-Type": "application/json",
          Accept: "application/vnd.github.v3+json"
        },
        body: JSON.stringify({
          message: "config: update keywords via web UI",
          content,
          sha: meta.sha
        })
      });
      if (!res.ok) throw new Error(await res.text());
      showToast("저장됨 ✓");
    } catch (e) {
      showToast("저장 실패: " + e.message);
    }
  }

  // ── 실행 버튼 ─────────────────────────────────────────
  async function runWorkflow() {
    const { token, repo } = getStoredPat();
    if (!token || !repo) { openSettings(); return; }

    const btn = document.getElementById("runBtn");
    btn.disabled = true;
    btn.innerHTML = '<div class="spinner"></div> 실행 중...';
    document.getElementById("runHint").textContent = "완료까지 15~20분 소요";

    try {
      const res = await fetch(`https://api.github.com/repos/${repo}/actions/workflows/daily.yml/dispatches`, {
        method: "POST",
        headers: {
          Authorization: `token ${token}`,
          "Content-Type": "application/json",
          Accept: "application/vnd.github.v3+json"
        },
        body: JSON.stringify({ ref: "main" })
      });
      if (!res.ok) throw new Error("workflow dispatch 실패: " + res.status);
      showToast("실행 시작됨! 완료까지 기다려주세요.");
      setTimeout(() => startPolling(token, repo), 5000);
    } catch (e) {
      showToast("실행 실패: " + e.message);
      resetRunBtn();
    }
  }

  function startPolling(token, repo) {
    let elapsed = 0;
    const MAX_WAIT = 30 * 60 * 1000; // 30분

    pollingInterval = setInterval(async () => {
      elapsed += 5000;
      if (elapsed > MAX_WAIT) {
        clearInterval(pollingInterval);
        showToast("시간 초과: 나중에 다시 확인해주세요.");
        resetRunBtn();
        return;
      }

      try {
        const res = await fetch(
          `https://api.github.com/repos/${repo}/actions/runs?per_page=1&event=workflow_dispatch`,
          { headers: { Authorization: `token ${token}`, Accept: "application/vnd.github.v3+json" } }
        );
        const data = await res.json();
        const run = data.workflow_runs?.[0];
        if (!run) return;

        if (run.status === "completed") {
          clearInterval(pollingInterval);
          if (run.conclusion === "success") {
            showToast("완료! 결과를 불러옵니다...");
            await scanAvailableDates();
          } else {
            showToast("실행 중 오류가 발생했습니다.");
          }
          resetRunBtn();
        }
      } catch { /* 네트워크 오류는 무시하고 계속 폴링 */ }
    }, 5000);
  }

  function resetRunBtn() {
    const btn = document.getElementById("runBtn");
    btn.disabled = false;
    btn.innerHTML = "▶ 실행";
    document.getElementById("runHint").textContent = "약 15~20분 소요";
  }

  // ── PAT 모달 ─────────────────────────────────────────
  function getStoredPat() {
    return {
      token: localStorage.getItem("gh_token") || "",
      repo:  localStorage.getItem("gh_repo")  || ""
    };
  }

  function checkPatModal() {
    const { token, repo } = getStoredPat();
    if (!token || !repo) openPatModal();
  }

  function openPatModal() {
    const { token, repo } = getStoredPat();
    document.getElementById("patInput").value = token;
    document.getElementById("repoInput").value = repo;
    document.getElementById("patModal").classList.remove("hidden");
  }

  function closePatModal() {
    document.getElementById("patModal").classList.add("hidden");
  }

  function openSettings() { openPatModal(); }

  function savePat() {
    const token = document.getElementById("patInput").value.trim();
    const repo  = document.getElementById("repoInput").value.trim();
    if (!token || !repo) { showToast("토큰과 레포 정보를 모두 입력해주세요."); return; }
    localStorage.setItem("gh_token", token);
    localStorage.setItem("gh_repo",  repo);
    closePatModal();
    showToast("저장됨 ✓");
  }

  // ── 엔터키 지원 ──────────────────────────────────────
  document.getElementById("newKeywordInput").addEventListener("keydown", e => {
    if (e.key === "Enter") addKeyword();
  });

  // ── 유틸 ─────────────────────────────────────────────
  function showEmptyState(msg) {
    document.getElementById("mainPanel").innerHTML = `<div class="empty-state">${msg}</div>`;
  }

  function showToast(msg) {
    const t = document.getElementById("toast");
    t.textContent = msg;
    t.classList.add("show");
    setTimeout(() => t.classList.remove("show"), 2500);
  }

  // ── 시작 ─────────────────────────────────────────────
  init();
</script>
</body>
</html>
```

- [ ] **Step 2: HTML 문법 검증**

브라우저에서 `docs/index.html`을 직접 열어 다음 확인:
- 페이지 로드 시 PAT 모달 표시 (localStorage 비어있으면)
- 사이드바 구조 정상 표시
- 콘솔 에러 없음

- [ ] **Step 3: 커밋**

```bash
git add docs/index.html
git commit -m "feat: add complete SPA frontend with sidebar, article cards, copy, and GitHub API integration"
```

---

## Chunk 4: 통합 및 배포

### Task 10: 로컬 통합 테스트

- [ ] **Step 1: 전체 테스트 스위트 실행**

```bash
pip install -r requirements.txt
pytest tests/ -v --tb=short
```
Expected: 모든 테스트 PASSED

- [ ] **Step 2: `run.py` 및 workflow 파일 문법 확인**

```bash
python -m py_compile src/naver_api.py src/article_fetcher.py src/summarizer.py src/output_writer.py run.py
echo "✅ Python 문법 오류 없음"
```

```bash
pip install pyyaml -q && python -c "import yaml; yaml.safe_load(open('.github/workflows/daily.yml'))" && echo "✅ YAML 문법 오류 없음"
```

- [ ] **Step 3: GitHub에 전체 push**

```bash
git push origin main
```

- [ ] **Step 3b: GitHub Pages 배포 대기**

  push 후 GitHub 레포 → Settings → Pages → "Your site is live at https://..." 메시지 확인.
  배포까지 보통 2~5분 소요. 메시지 확인 후 다음 단계 진행.

---

### Task 11: GitHub 설정 및 첫 실행

- [ ] **Step 1: 네이버 개발자센터 API 발급**

  1. https://developers.naver.com 접속 후 로그인
  2. 상단 "Application" → "애플리케이션 등록"
  3. 사용 API: "검색" 체크
  4. 등록 완료 후 `Client ID`, `Client Secret` 복사

- [ ] **Step 2: Gemini API 키 발급**

  1. https://aistudio.google.com/apikey 접속
  2. "Create API Key" → Gemini 2.5 Flash 프로젝트 선택
  3. API 키 복사

- [ ] **Step 3: GitHub PAT 발급**

  1. GitHub → Settings → Developer settings → Personal access tokens → Fine-grained tokens
  2. Repository access: 이 레포만 선택
  3. Permissions: Contents (read/write), Actions (read/write)
  4. PAT 복사

- [ ] **Step 4: GitHub Secrets 등록**

  GitHub 레포 → Settings → Secrets and variables → Actions → New repository secret:
  - `NAVER_CLIENT_ID`
  - `NAVER_CLIENT_SECRET`
  - `GEMINI_API_KEY`

  > `GH_TOKEN`은 웹 UI의 localStorage에 저장되는 PAT로, GitHub Actions Secret에는 등록하지 않아도 됨 (workflow는 기본 `GITHUB_TOKEN`으로 docs/data/ 커밋 가능)

- [ ] **Step 5: GitHub Pages 활성화**

  GitHub 레포 → Settings → Pages → Source: `Deploy from a branch` → Branch: `main` / Folder: `/docs`

- [ ] **Step 6: 웹 UI에서 첫 설정**

  1. GitHub Pages URL 열기
  2. PAT 모달에 토큰과 `owner/repo` 입력 후 저장
  3. 사이드바에 키워드 추가 (예: 삼성전자)
  4. "실행" 버튼 클릭 → 완료까지 대기

- [ ] **Step 7: 결과 확인**

  실행 완료 후 기사 카드가 메인 패널에 표시되면 성공.

---

