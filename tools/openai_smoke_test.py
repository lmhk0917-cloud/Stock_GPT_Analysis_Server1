"""Live OpenAI API smoke test.

This script uses OPENAI_API_KEY from the process environment or .env.local.
It prints only model/usage/safe response metadata, never the key.
"""

import os
import sys

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if ROOT not in sys.path:
    sys.path.insert(0, ROOT)

from analysis.gpt_analyzer import GPTAnalyzer
from app.config import OPENAI_API_KEY


def main():
    if not OPENAI_API_KEY:
        print("OPENAI_API_KEY=MISSING")
        raise SystemExit(2)

    analyzer = GPTAnalyzer()
    answer = analyzer.chat([
        {
            "role": "user",
            "content": "서버 GPT 연결 smoke test입니다. 한 문장으로 응답하세요.",
        }
    ])
    status = "OK" if answer and not analyzer.last_error_message else "FAIL"
    print("OPENAI_SMOKE_TEST={}".format(status))
    print("MODEL={}".format(analyzer.last_model))
    print("USAGE={}".format(analyzer.last_usage))
    print("ANSWER_PREVIEW={}".format((answer or "")[:120].replace("\n", " ")))
    if analyzer.last_error_message:
        print("ERROR={}".format(analyzer.last_error_message))
        raise SystemExit(1)


if __name__ == "__main__":
    main()
