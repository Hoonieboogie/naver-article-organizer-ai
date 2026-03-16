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
    MODEL = "gemini-2.0-flash"

    def __init__(self, api_key: str):
        self._client = genai.Client(api_key=api_key)
        self._call_count = 0

    def summarize(self, title: str, content: str) -> str:
        """기사 제목과 본문을 받아 요약문을 반환한다. 실패 시 빈 문자열 반환."""
        if self._call_count > 0:
            time.sleep(6)  # 분당 10회 = 6초 간격

        prompt = PROMPT_TEMPLATE.format(title=title, content=content[:8000])
        try:
            response = self._client.models.generate_content(
                model=self.MODEL,
                contents=prompt,
            )
            self._call_count += 1
            return response.text.strip()
        except Exception as e:
            print(f"    [WARN] 요약 실패 ({type(e).__name__}): {e}")
            return ""
