"""OpenAI wrapper with a mock-safe default path."""

import json
import time

from app.config import GPT_MAX_TOKENS, GPT_MODEL, OPENAI_API_KEY


class GPTAnalyzer:
    def __init__(self, api_key=None, model=None):
        self.api_key = api_key or OPENAI_API_KEY
        self.model = model or GPT_MODEL
        self.last_model = self.model
        self.last_usage = {}
        self.last_error_message = None

    def analyze(self, market_summaries, settings=None):
        if not self.api_key:
            return self.mock_analysis(market_summaries)

        try:
            from openai import OpenAI, RateLimitError
        except Exception as exc:
            self.last_error_message = str(exc)
            return self.mock_analysis(market_summaries, prefix="OpenAI SDK unavailable")

        prompt = self._build_prompt(market_summaries, settings=settings)
        client = OpenAI(api_key=self.api_key)
        wait = 2

        for _ in range(3):
            try:
                response = client.chat.completions.create(
                    model=self.model,
                    messages=[
                        {
                            "role": "system",
                            "content": "너는 한국 주식 분석 보조 AI다. 확정적 매수/매도 지시를 하지 않는다.",
                        },
                        {"role": "user", "content": prompt},
                    ],
                    max_tokens=GPT_MAX_TOKENS,
                )
                self.last_model = getattr(response, "model", self.model)
                self.last_usage = self._extract_usage(response)
                return response.choices[0].message.content
            except RateLimitError:
                self.last_error_message = "OpenAI rate limit"
                time.sleep(wait)
                wait *= 2
            except Exception as exc:
                self.last_error_message = str(exc)
                return "GPT call error: {}".format(exc)

        return "GPT analysis failed because rate limit retries were exceeded"

    def chat(self, messages, system_prompt=None):
        if not self.api_key:
            return self._mock_chat(messages)

        try:
            from openai import OpenAI, RateLimitError
        except Exception as exc:
            self.last_error_message = str(exc)
            return self._mock_chat(messages, prefix="OpenAI SDK unavailable")

        api_messages = []
        if system_prompt:
            api_messages.append({"role": "system", "content": system_prompt})
        api_messages.extend(messages)

        client = OpenAI(api_key=self.api_key)
        wait = 2
        for _ in range(3):
            try:
                response = client.chat.completions.create(
                    model=self.model,
                    messages=api_messages,
                    max_tokens=GPT_MAX_TOKENS,
                )
                self.last_model = getattr(response, "model", self.model)
                self.last_usage = self._extract_usage(response)
                return response.choices[0].message.content
            except RateLimitError:
                self.last_error_message = "OpenAI rate limit"
                time.sleep(wait)
                wait *= 2
            except Exception as exc:
                self.last_error_message = str(exc)
                return "GPT call error: {}".format(exc)

        return "GPT chat failed because rate limit retries were exceeded"

    def mock_analysis(self, market_summaries, prefix="mock analysis"):
        symbols = ["{}({})".format(item.get("name"), item.get("code")) for item in market_summaries]
        return "{}: {} symbols processed without a live GPT call".format(prefix, ", ".join(symbols))

    def _mock_chat(self, messages, prefix="mock chat"):
        last_user = ""
        for message in reversed(messages):
            if message.get("role") == "user":
                last_user = message.get("content", "")
                break
        self.last_model = "mock"
        self.last_usage = {
            "prompt_tokens": sum(len(item.get("content", "")) // 4 for item in messages),
            "completion_tokens": 40,
            "total_tokens": sum(len(item.get("content", "")) // 4 for item in messages) + 40,
        }
        return "{}: 서버가 사용자 메모리와 최근 대화 맥락을 기준으로 요청을 접수했습니다. 요청='{}'".format(
            prefix,
            last_user[:120],
        )

    def _build_prompt(self, market_summaries, settings=None):
        data_json = json.dumps(market_summaries, ensure_ascii=False, separators=(",", ":"), default=str)
        return (
            "다음 데이터는 서버에서 공통 생성한 종목 분석 입력이다. "
            "개인 계좌/보유수량 기반 조언 없이 조건부 참고 분석만 작성하라.\n\n"
            + data_json
        )

    def _extract_usage(self, response):
        usage = getattr(response, "usage", None)
        if not usage:
            return {}
        return {
            "prompt_tokens": getattr(usage, "prompt_tokens", None),
            "completion_tokens": getattr(usage, "completion_tokens", None),
            "total_tokens": getattr(usage, "total_tokens", None),
        }
