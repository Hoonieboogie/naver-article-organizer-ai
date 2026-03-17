import json
import os
from datetime import datetime


class OutputWriter:
    def __init__(self, output_dir: str = "docs/data"):
        self.output_dir = output_dir
        os.makedirs(output_dir, exist_ok=True)

    def write(self, run_date: datetime, section_results: list[dict]) -> str:
        """날짜별 JSON 파일을 docs/data/{YYYY-MM-DD}.json 에 저장하고 index.json 갱신."""
        date_str = run_date.strftime("%Y-%m-%d")
        payload = {
            "date": date_str,
            "generated_at": run_date.isoformat(),
            "sections": section_results,
        }
        path = os.path.join(self.output_dir, f"{date_str}.json")
        with open(path, "w", encoding="utf-8") as f:
            json.dump(payload, f, ensure_ascii=False, indent=2)

        self._update_index(date_str)
        return path

    def _update_index(self, date_str: str) -> None:
        """docs/data/index.json 에 날짜 목록을 최신순으로 유지한다."""
        index_path = os.path.join(self.output_dir, "index.json")
        if os.path.exists(index_path):
            with open(index_path, encoding="utf-8") as f:
                dates = json.load(f).get("dates", [])
        else:
            dates = []
        if date_str not in dates:
            dates.append(date_str)
        dates = sorted(set(dates), reverse=True)
        with open(index_path, "w", encoding="utf-8") as f:
            json.dump({"dates": dates}, f, ensure_ascii=False, indent=2)
