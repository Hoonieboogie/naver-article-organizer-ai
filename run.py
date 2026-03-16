"""
네이버 뉴스 모니터 메인 실행 스크립트.
환경 변수: NAVER_CLIENT_ID, NAVER_CLIENT_SECRET, GEMINI_API_KEY
"""
import argparse
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


def run_fetch(keywords, articles_per_keyword, run_date, naver, writer):
    """Naver API 호출 → 기사 목록 저장 (요약 없음)."""
    total_kw = len(keywords)
    keyword_results = []

    for kw_idx, keyword in enumerate(keywords, 1):
        print(f"[STATUS] 기사 수집 중 · {keyword} ({kw_idx}/{total_kw})")
        articles_meta = naver.fetch_articles(keyword, max_count=articles_per_keyword, run_date=run_date)
        print(f"  → {len(articles_meta)}개 기사 발견")

        articles_output = []
        for meta in articles_meta:
            articles_output.append({
                "title": meta["title"],
                "url": meta["url"],
                "published_at": meta["published_at"],
                "description": meta["description"],
                "summary": "",
                "source": "pending",
            })

        keyword_results.append({"keyword": keyword, "articles": articles_output})

    print("[STATUS] 결과 저장 중")
    output_path = writer.write(run_date=run_date, keyword_results=keyword_results, summarized=False)
    print(f"\n✅ 수집 완료: {output_path}")


def run_summarize(run_date, fetcher, summarizer, writer):
    """기존 JSON을 읽어 Gemini 요약 추가 후 저장."""
    date_str = run_date.strftime("%Y-%m-%d")
    data_path = os.path.join("docs/data", f"{date_str}.json")

    if not os.path.exists(data_path):
        print(f"[ERROR] {data_path} 없음. 먼저 fetch를 실행하세요.")
        sys.exit(1)

    with open(data_path, encoding="utf-8") as f:
        data = json.load(f)

    keyword_results = data.get("keywords", [])
    total_kw = len(keyword_results)

    for kw_idx, kw_data in enumerate(keyword_results, 1):
        keyword = kw_data["keyword"]
        articles = kw_data["articles"]
        total_art = len(articles)

        for i, article in enumerate(articles, 1):
            print(f"[STATUS] 분석 · 요약 중 · {keyword} ({kw_idx}/{total_kw}) — 기사 {i}/{total_art}")
            fetch_result = fetcher.fetch(article["url"], fallback_description=article.get("description", ""))
            summary = summarizer.summarize(title=article["title"], content=fetch_result.content)
            article["summary"] = summary
            article["source"] = fetch_result.source
            print(f"    요약 완료 ({len(summary)}자)")

    print("[STATUS] 결과 저장 중")
    output_path = writer.write(run_date=run_date, keyword_results=keyword_results, summarized=True)
    print(f"\n✅ 요약 완료: {output_path}")


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--phase", default="all", choices=["fetch", "summarize", "all"])
    args = parser.parse_args()

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
    print(f"실행 시작 [{args.phase}]: {run_date.isoformat()}")
    print(f"키워드: {keywords} / 키워드당 기사 수: {articles_per_keyword}")

    writer = OutputWriter()

    if args.phase in ("fetch", "all"):
        naver = NaverNewsClient(client_id=naver_id, client_secret=naver_secret)
        run_fetch(keywords, articles_per_keyword, run_date, naver, writer)

    if args.phase in ("summarize", "all"):
        fetcher = ArticleFetcher(gemini_api_key=gemini_key)
        summarizer = Summarizer(api_key=gemini_key)
        run_summarize(run_date, fetcher, summarizer, writer)


if __name__ == "__main__":
    main()
