# DB Schema

초기 DB는 SQLite다. Web/모바일 앱 확장 시 PostgreSQL로 옮기기 쉽도록 사용자별 테이블과 공통 시장/분석 테이블을 분리했다.

## User Tables

- `users`: login ID, 표시명, role, Telegram chat ID, 활성 상태
- `user_watchlists`: 사용자별 관심종목
- `user_settings`: 사용자별 JSON 설정
- `user_alert_rules`: 사용자별 이벤트 알림 조건
- `user_memory`: 사용자별 장기 메모리와 선호 정보
- `chat_sessions`: 사용자별 GPT 대화 세션
- `chat_messages`: 세션별 대화 메시지
- `user_report_views`: 사용자별 분석 결과 조회 이력

## Broker / Order Tables

- `broker_credentials`: 사용자별 증권사 API 키 암호화 저장소
- `order_requests`: 주문 요청, 승인 문구, 차단/대기 상태 감사 로그

## Shared Market Tables

- `market_symbols`: provider-neutral 종목 메타데이터
- `market_prices`: 공통 OHLCV 저장소
- `analysis_results`: 공통 분석 결과
- `event_logs`: 공통 이벤트 감지 로그
- `gpt_call_logs`: GPT 호출 감사 로그
- `api_request_logs`: 서버 요청/사용량 감사 로그
- `notification_logs`: 사용자별 발송 결과

## 원칙

- GPT 결과는 사용자마다 중복 생성하지 않는다.
- 사용자 설정은 초기에는 필터링, 알림, 표시 방식에 적용한다.
- 증권사 credential은 평문 저장하지 않는다.
- 주문 실행은 기본 비활성화하고, 요청과 차단/승인 상태만 감사 로그에 남긴다.
