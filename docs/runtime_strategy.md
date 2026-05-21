# Runtime Strategy

## 원칙

서버 본체는 `Python 3.11+ 64-bit`를 기준으로 운영한다. `py37_32`는 키움 OpenAPI+를 계속 써야 할 때만 별도 legacy worker로 유지한다.

## Server Runtime

권장:

- Python 3.11 또는 3.12 64-bit
- FastAPI / Uvicorn
- OpenAI SDK
- SQLite 초기 운영, 이후 PostgreSQL 전환 가능
- KIS REST, Kiwoom REST 같은 HTTP 기반 adapter

역할:

- 사용자 인증/ID
- 사용자 설정/메모리/채팅
- OpenAI gateway
- 사용량/요청 감사
- broker credential 암호화 저장
- 주문 요청 gate

## Kiwoom Legacy Runtime

대상:

- Kiwoom OpenAPI+ Windows COM/OCX
- QAxWidget
- 32-bit Python 제약이 필요한 경우

역할:

- 키움 전용 로그인/수집 worker
- 서버 DB 또는 HTTP endpoint로 provider-neutral 데이터 전달
- 서버 본체 import 금지

## Adapter Boundary

서버 본체는 `market_data/adapters/base.py`의 provider-neutral interface만 본다. 증권사별 인증, token, endpoint, TR ID는 각 adapter 안에 둔다.

```text
server 64-bit
  -> broker adapter interface
     -> mock adapter
     -> kis_rest_adapter
     -> kiwoom_rest_adapter
     -> kiwoom_legacy_worker bridge
```

## Migration Steps

1. 서버 본체를 새 64-bit venv에서 설치한다.
2. `tools/server_smoke_test.py`와 `tools/stability_check.py`를 실행한다.
3. KIS REST adapter에 실제 사용자 credential을 등록해 조회 API부터 연결한다.
4. 주문 API는 `ENABLE_ORDER_API=0` 기본값을 유지한 채 요청/승인 로그만 검증한다.
5. 키움 OpenAPI+가 필요해지면 `legacy/kiwoom_worker.py`를 별도 `py37_32` 프로세스로 실행한다.
