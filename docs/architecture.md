# Architecture

## 경계

이 프로젝트는 개인용 Kiwoom/OpenAI 앱의 실행 환경과 분리된 private beta 서버형 구조다. 서버/운영자 계정이 시장 데이터를 수집하고, 사용자는 개인 ID로 관심종목과 알림 조건만 관리한다.

서버 본체는 `Python 3.11+ 64-bit` 기준이다. `py37_32`는 키움 OpenAPI+ legacy worker 외에는 사용하지 않는다.

## 모듈

- `app`: 설정과 CLI 진입점
- `core`: SQLite 연결, schema, 사용자/감사 저장소
- `broker`: 주문 요청 gate. 실제 주문 실행은 아직 연결하지 않고 기본 차단
- `market_data`: provider adapter와 mock-first worker
- `analysis`: 지표, 이벤트 감지, GPT 분석 wrapper
- `delivery`: 사용자별 알림 라우팅
- `server`: FastAPI 엔드포인트, dependency-free 개발 서버, 채팅 gateway, 서비스 레이어
- `tools`: 오프라인 검증 도구

## 분석 흐름

1. 사용자 watchlist를 합쳐 unique symbol 목록을 만든다.
2. adapter가 symbol별 OHLCV를 수집한다.
3. 공통 지표와 이벤트를 계산한다.
4. GPT는 종목/시각 단위 공통 결과로 한 번만 호출한다. mock 모드에서는 호출하지 않는다.
5. 사용자의 watchlist와 alert rule 기준으로 결과와 알림을 필터링한다.
6. `analysis_results`, `event_logs`, `notification_logs`에 남긴다.

## Adapter 정책

Windows 전용 QAxWidget이나 증권사 REST 인증 코드는 adapter 경계 안에만 들어가야 하며, API 서버와 저장소가 직접 provider SDK를 import하지 않는다.

KIS REST는 `market_data/adapters/kis_rest_adapter.py`에 인증 token, base URL, 시세 조회 endpoint를 모아둔다. Kiwoom OpenAPI+는 `legacy/kiwoom_worker.py`에서 별도 프로세스로 격리한다.

## 사용자 메모리와 GPT 대화

사용자별 설정은 `user_settings`, 장기 성향/선호/메모는 `user_memory`, 대화 이력은 `chat_sessions`와 `chat_messages`에 분리 저장한다. GPT 호출은 서버의 OpenAI adapter를 거쳐야 하며, 사용자의 broker secret 원문은 prompt에 포함하지 않는다.

`ChatService`는 사용자 메모리, 최근 대화, 최신 분석 결과를 묶어 GPT gateway로 전달한다. OpenAI API 키가 없으면 mock 응답으로 동작하고, 호출 결과는 `gpt_call_logs`에 남긴다.

## API 서버

정식 경로는 `server/api.py`의 FastAPI 서버다. 현재 개발 환경처럼 FastAPI가 없는 경우 `server/simple_server.py`를 통해 `/health`, `/users`, `/users/{id}/chat`, `/admin/overview`, `/admin/run-analysis`를 표준 라이브러리 HTTP 서버로 확인할 수 있다.

## Broker Credential / Order Gate

사용자별 한국투자증권 REST API 키는 `broker_credentials`에 암호화 envelope로 저장한다. 서버 운영자는 credential metadata만 API에서 확인하고, 평문 키는 broker adapter 호출 시점에만 복호화하는 구조다.

주문 기능은 scaffold만 있다. `ENABLE_ORDER_API=0`이면 모든 주문 요청은 `blocked_order_api_disabled` 상태로 감사 로그에 남는다. `ENABLE_ORDER_API=1`이어도 `REQUIRE_ORDER_CONFIRMATION=1`이면 승인 문구가 일치해야 `accepted_pending_adapter` 상태가 된다.

## 운영 감사

관리자는 `api_request_logs`, `gpt_call_logs`, `notification_logs`, `order_requests`를 통해 사용자별 사용량, 요청 경로, 주문 시도, 알림 결과를 확인한다.
