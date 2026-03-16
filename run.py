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
    total_kw = len(keywords)

    for kw_idx, keyword in enumerate(keywords, 1):
        print(f"[STATUS] 기사 수집 중 · {keyword} ({kw_idx}/{total_kw})")
        articles_meta = naver.fetch_articles(keyword, max_count=articles_per_keyword, run_date=run_date)
        print(f"  → {len(articles_meta)}개 기사 발견")

        articles_output = []
        total_art = len(articles_meta)
        for i, meta in enumerate(articles_meta, 1):
            print(f"[STATUS] 분석 · 요약 중 · {keyword} ({kw_idx}/{total_kw}) — 기사 {i}/{total_art}")

            fetch_result = fetcher.fetch(meta["url"], fallback_description=meta["description"])
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

    print("[STATUS] 결과 저장 중")
    output_path = writer.write(run_date=run_date, keyword_results=keyword_results)
    print(f"\n✅ 완료: {output_path}")


if __name__ == "__main__":
    main()
