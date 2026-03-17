"""
네이버 뉴스 모니터 메인 실행 스크립트.
환경 변수: NAVER_CLIENT_ID, NAVER_CLIENT_SECRET
"""
import os
import sys
import json
from datetime import datetime, timezone, timedelta

from src.naver_api import NaverNewsClient
from src.output_writer import OutputWriter

KST = timezone(timedelta(hours=9))


def load_config(path: str = "config.json") -> dict:
    with open(path, encoding="utf-8") as f:
        return json.load(f)


def main():
    naver_id = os.environ["NAVER_CLIENT_ID"]
    naver_secret = os.environ["NAVER_CLIENT_SECRET"]

    config = load_config()
    sections = config.get("sections", [])
    articles_per_keyword = config.get("articles_per_keyword", 10)

    # 모든 섹션의 키워드를 모아서 수집
    all_keywords = []
    for sec in sections:
        for kw in sec.get("keywords", []):
            all_keywords.append((sec["name"], kw))

    if not all_keywords:
        print("config.json에 키워드가 없습니다. 종료합니다.")
        sys.exit(0)

    run_date = datetime.now(tz=KST)
    print(f"실행 시작: {run_date.isoformat()}")
    print(f"섹션: {[s['name'] for s in sections]} / 키워드당 기사 수: {articles_per_keyword}")

    naver = NaverNewsClient(client_id=naver_id, client_secret=naver_secret)
    writer = OutputWriter()

    # 섹션별로 결과 구성
    section_results = []
    total_kw = len(all_keywords)
    kw_idx = 0

    errors = []
    for sec in sections:
        keyword_results = []
        for keyword in sec.get("keywords", []):
            kw_idx += 1
            print(f"[STATUS] 기사 수집 중 · [{sec['name']}] {keyword} ({kw_idx}/{total_kw})")
            try:
                articles_meta = naver.fetch_articles(keyword, max_count=articles_per_keyword, run_date=run_date)
            except Exception as e:
                print(f"  ⚠️ 수집 실패 ({type(e).__name__}): {e}")
                errors.append(keyword)
                keyword_results.append({"keyword": keyword, "articles": []})
                continue
            print(f"  → {len(articles_meta)}개 기사 발견")

            articles_output = []
            for meta in articles_meta:
                articles_output.append({
                    "title": meta["title"],
                    "url": meta["url"],
                    "published_at": meta["published_at"],
                    "description": meta["description"],
                    "source_name": meta.get("source_name", ""),
                })

            keyword_results.append({"keyword": keyword, "articles": articles_output})

        section_results.append({
            "name": sec["name"],
            "keywords": keyword_results,
        })

    print("[STATUS] 결과 저장 중")
    output_path = writer.write(run_date=run_date, section_results=section_results)
    if errors:
        print(f"\n⚠️ 수집 실패 키워드: {errors}")
    print(f"\n✅ 수집 완료: {output_path}")


if __name__ == "__main__":
    main()
