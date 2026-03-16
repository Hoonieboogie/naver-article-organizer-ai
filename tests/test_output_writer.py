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
