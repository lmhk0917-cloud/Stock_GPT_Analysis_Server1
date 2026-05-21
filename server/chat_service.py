"""Server-side GPT chat orchestration."""

from analysis.gpt_analyzer import GPTAnalyzer
from core.audit_store import AuditStore
from core.database import dumps_json, utc_now
from core.memory_store import UserMemoryStore
from core.user_store import UserStore


class ChatService:
    def __init__(self, conn, analyzer=None):
        self.conn = conn
        self.users = UserStore(conn)
        self.memory = UserMemoryStore(conn)
        self.audit = AuditStore(conn)
        self.analyzer = analyzer or GPTAnalyzer()

    def ask(self, user_id, content, session_id=None, title=None):
        user = self.users.get_user(user_id)
        if not user:
            raise ValueError("user not found")

        if session_id is None:
            session_id = self.memory.create_chat_session(user_id, title or content[:40] or "New chat")

        self.memory.add_chat_message(session_id, "user", content)
        messages = self._build_messages(user_id, session_id)
        started_at = utc_now()
        answer = self.analyzer.chat(messages, system_prompt=self._system_prompt())
        finished_at = utc_now()
        self.memory.add_chat_message(
            session_id,
            "assistant",
            answer,
            token_count=self.analyzer.last_usage.get("completion_tokens"),
        )
        self.audit.save_gpt_call(
            started_at,
            finished_at,
            "ok" if not self.analyzer.last_error_message else "error",
            requested_count=1,
            symbols=[],
            model=self.analyzer.last_model,
            usage=self.analyzer.last_usage,
            result_preview=answer,
        )
        return {
            "session_id": session_id,
            "answer": answer,
            "model": self.analyzer.last_model,
            "usage": self.analyzer.last_usage,
            "error": self.analyzer.last_error_message,
        }

    def _build_messages(self, user_id, session_id):
        memories = self.memory.list_memory(user_id)[:10]
        reports = self.audit.latest_reports_for_user(user_id, limit=5)
        recent_messages = self.memory.list_chat_messages(session_id)[-10:]
        context = {
            "user_memory": memories,
            "latest_reports": reports,
            "safety_boundary": (
                "개인 API secret, access token, 계좌번호 원문은 GPT 입력에 포함하지 않는다. "
                "매수/매도 확정 지시가 아니라 조건부 참고 분석으로 답한다."
            ),
        }
        messages = [
            {
                "role": "system",
                "content": "서버 저장 컨텍스트 JSON: " + dumps_json(context),
            }
        ]
        for message in recent_messages:
            role = message.get("role")
            if role in ("user", "assistant", "system"):
                messages.append({"role": role, "content": message.get("content", "")})
        return messages

    def _system_prompt(self):
        return (
            "너는 private beta용 한국 주식 분석 보조 서버의 대화 엔진이다. "
            "사용자별 메모리와 서버 분석 결과를 참고하되, 증권사 API 키/토큰/계좌번호 원문은 절대 언급하지 않는다. "
            "주문 실행은 서버의 별도 승인 gate가 담당하며, 너는 주문을 직접 실행했다고 말하지 않는다."
        )
