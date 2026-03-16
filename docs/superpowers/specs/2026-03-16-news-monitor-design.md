# 네이버 뉴스 모니터 — 디자인 스펙

**날짜:** 2026-03-16
**상태:** 승인됨

---

## 1. 개요

키워드(회사/브랜드명)별로 네이버 뉴스를 수집하고, AI가 기사 원문을 읽고 핵심 내용을 요약해 웹페이지에 표시하는 시스템. 단일 사용자용, 완전 무료 인프라.

---

## 2. 인프라 및 배포

| 항목 | 선택 | 이유 |
|---|---|---|
| 소스 관리 | GitHub (private repo) | URL 비공개로 인증 대체 |
| 스케줄러 | GitHub Actions | 무료 월 2,000분, cron 지원 |
| 웹 호스팅 | GitHub Pages | 무료 정적 호스팅 |
| AI 요약 | Gemini 2.5 Flash API | 무료 티어 250 req/day |
| 별도 서버/DB | 없음 | JSON 파일로 대체 |

---

## 3. 실행 트리거

두 가지 모드를 모두 지원한다:

1. **자동 실행**: `config.json`에 키워드가 설정된 경우, GitHub Actions cron으로 매일 **10:00 KST (UTC 01:00)** 자동 실행
2. **수동 실행**: 웹 페이지의 "실행" 버튼 클릭 → GitHub API `workflow_dispatch` 호출 → Actions 즉시 실행

---

## 4. 디렉토리 구조

```
repo/
├── .github/
│   └── workflows/
│       └── daily.yml          # cron + workflow_dispatch 트리거
├── run.py                     # 메인 수집/요약 스크립트
├── config.json                # 키워드 목록, 기사 수 설정
├── requirements.txt
└── docs/                      # GitHub Pages 루트
    ├── index.html             # 고정 SPA 템플릿
    └── data/
        ├── 2026-03-15.json
        └── 2026-03-16.json    # 날짜별 결과 (누적 보관)
```

---

## 5. 데이터 스키마

### `config.json`

```json
{
  "keywords": ["삼성전자", "LG전자", "카카오"],
  "articles_per_keyword": 10,
  "schedule": "0 1 * * *"
}
```

### `docs/data/{YYYY-MM-DD}.json`

```json
{
  "date": "2026-03-16",
  "generated_at": "2026-03-16T10:05:32",
  "keywords": [
    {
      "keyword": "삼성전자",
      "articles": [
        {
          "title": "삼성전자, 3나노 양산 본격화",
          "url": "https://...",
          "published_at": "2026-03-16T08:30:00",
          "summary": "삼성전자는 3나노 2세대 공정 양산을 시작했으며...",
          "source": "url_context"
        }
      ]
    }
  ]
}
```

`source` 필드 값: `url_context` | `bs4` | `description`

---

## 6. 기사 수집 파이프라인 (`run.py`)

### 6-1. 네이버 뉴스 API

- **API**: 네이버 검색 API (뉴스)
- **인증**: Client ID / Client Secret (GitHub Actions Secret으로 관리)
- **기간 필터**: 전날 10:00 KST ~ 당일 09:00 KST 사이 발행 기사 (23시간 윈도우 — 당일 실행과 겹침 방지)
- **날짜 변환**: 네이버 API `pubDate` 필드(RFC 822) → ISO 8601 변환은 `run.py`가 담당
- **수량**: `config.json`의 `articles_per_keyword` 값 (최대 20개)

### 6-2. 기사 원문 수집 — 3단계 Fallback

```
1️⃣ Gemini url_context tool
   └─ 실패 시 ↓
2️⃣ Python requests + BeautifulSoup4 크롤링
   (User-Agent 헤더 설정, 한국 뉴스 사이트 대부분 통과)
   └─ 실패 시 ↓
3️⃣ 네이버 API description (발췌문)
   (항상 성공, 내용은 얕음 — UI에 ⚠️ 표시)
```

### 6-3. AI 요약 (Gemini 2.5 Flash)

- **프롬프트 방침**: 기사에 등장한 단어만 사용해 핵심 내용을 빠짐없이 요약. 중요한 수치·인물·사건 반드시 포함. 길이 제한 없음.
- **Rate limit 대응**: 분당 10회 제한 → 기사 간 6초 딜레이 적용 (전체 기사 순차 처리, 키워드 간 병렬 처리 없음)
- **예상 소요시간**: 최대 180기사 기준 약 18분 (10시 30분 확인 시 여유 있음)

---

## 7. 웹 UI

### 7-1. 레이아웃

**사이드바 + 메인 패널** 구조:

| 사이드바 | 메인 패널 |
|---|---|
| 키워드 목록 (기사 수 뱃지) | 선택된 키워드의 기사 카드 목록 |
| 키워드 추가/삭제 | 기사 제목 + 요약 + 링크 |
| 기사 수(k) 설정 | 각 기사에 체크박스 |
| 날짜 선택 (과거 기록) | 섹션 우측 상단 "복사" 버튼 |
| "실행" 버튼 | - |

### 7-2. 기사 카드

- 체크박스 (선택/해제)
- 기사 제목 + 외부 링크 아이콘 (↗)
- AI 요약 (가변 길이, 핵심 내용 전체 포함)
- 메타정보: 언론사 · 발행 시각 · source 방법
- `description` fallback 기사에는 ⚠️ 경고 표시

### 7-3. 복사 기능

섹션의 "📋 선택 항목 복사" 버튼 클릭 시 클립보드에 복사:

```
삼성전자
* https://...
* https://...
```

선택된 기사가 없으면 버튼 비활성화.

### 7-4. 키워드 관리

- 웹 UI에서 키워드 추가/삭제 → GitHub API 호출 → `config.json` 업데이트 → 다음 실행에 반영
- **GitHub PAT 초기 설정**: 페이지 최초 로드 시 localStorage에 토큰이 없으면 모달 표시 → 토큰 입력 → `localStorage`에 저장. 이후 방문 시 모달 없이 자동 로드.
- 사이드바 하단 "⚙️ 설정" 버튼으로 언제든 토큰 재입력 가능
- 기사 수(k) 조정도 동일하게 GitHub API로 처리

### 7-5. 실행 상태 표시

- 실행 버튼 클릭 후 → 버튼 비활성화 + 스피너 표시
- GitHub Actions API (`GET /repos/{owner}/{repo}/actions/runs`) 를 **5초 간격**으로 폴링
- 최대 폴링 시간: **30분** (타임아웃 시 에러 메시지 표시 후 버튼 재활성화)
- workflow 상태: `queued` / `in_progress` → 스피너 유지
- workflow 상태: `completed` + conclusion `success` → 최신 JSON 자동 로드 후 표시
- workflow 상태: `completed` + conclusion `failure` → "실행 중 오류가 발생했습니다" 메시지 + 버튼 재활성화

---

## 8. 보안

- **Private repo**: URL 비공개로 외부 접근 차단
- **GitHub Token**: `localStorage` 저장 (단일 사용자 환경)
- **API 키**: GitHub Actions Secret으로 관리 (NAVER_CLIENT_ID, NAVER_CLIENT_SECRET, GEMINI_API_KEY, GH_TOKEN)

---

## 9. 네이버 뉴스 API 발급 안내

1. [네이버 개발자센터](https://developers.naver.com) 접속
2. 애플리케이션 등록 → "검색" API 선택
3. Client ID / Client Secret 발급 (5분 소요)

---

## 10. 범위 외 (이번 버전 미포함)

- 알림 기능 (이메일, Slack 등)
- 기사 감성 분석
- 키워드 간 비교/트렌드 차트
- 모바일 최적화
