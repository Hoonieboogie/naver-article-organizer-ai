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
