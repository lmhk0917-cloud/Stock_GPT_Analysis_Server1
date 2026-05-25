# Stock_GPT_Analysis_Server1

Kiwoom/OpenAI 개인용 주가 분석 프로젝트를 기반으로 분리한 서버형 멀티유저 MVP다. 초기 목표는 소수 사용자가 각자 관심종목, 설정, 알림 조건을 갖고 접속하되, 시장 데이터 수집과 공통 분석 결과는 서버가 한 번만 생성해 공유하는 구조다.

서버 본체는 `Python 3.11+ 64-bit` 기준으로 정리했다. `py37_32`는 키움 OpenAPI+가 필요할 때만 `legacy/kiwoom_worker.py`에서 별도 프로세스로 유지한다.

## 현재 범위

- SQLite 기반 `users`, `user_watchlists`, `user_settings`, `user_alert_rules` 추가
- 공통 시장 데이터와 사용자별 데이터를 분리한 DB 스키마
- Kiwoom/QAxWidget 의존을 adapter 경계 밖으로 격리
- KIS REST adapter 뼈대 추가
- 키움 OpenAPI+는 legacy worker 전용으로 분리
- `mock_adapter.py` 기반 오프라인 시세 생성
- 공통 분석 결과를 사용자 watchlist 기준으로 필터링
- console 알림 로그 저장
- 사용자별 broker API credential 암호화 저장
- 주문 요청 scaffold 추가, 기본 비활성화
- 주문 승인 문구 요구 기능 추가
- 사용자별 메모리와 채팅 세션/메시지 저장
- 관리자 요청 로그 저장
- 사용자 메모리와 최신 분석 결과를 포함하는 GPT 채팅 gateway
- 브라우저에서 확인 가능한 관리자 대시보드
- FastAPI 미설치 환경에서도 확인 가능한 표준 라이브러리 개발용 HTTP 서버
- FastAPI 확장용 API 파일 제공

자동매매와 실제 주문 실행은 초기 범위에서 제외하되, 주문 요청/승인/차단 로그 구조는 만들어두었다. 외부 공개나 유료 제공 단계에서는 법률/약관 검토가 필요하다.

## 보안/주문 기본값

증권사 API 키 저장에는 `CREDENTIAL_MASTER_KEY`가 필요하다. 이 값이 없으면 broker credential 저장 API는 실패한다. 실제 주문 실행은 `ENABLE_ORDER_API=0`이 기본값이라 차단된다. 나중에 주문 adapter를 붙이더라도 `REQUIRE_ORDER_CONFIRMATION=1`이면 `ORDER_CONFIRMATION_TEXT`와 동일한 승인 문구가 들어온 요청만 다음 단계로 넘어간다.

## 로컬 API 키 설정

OpenAI API 키를 직접 발급받은 뒤에는 `.env.local.example`을 `.env.local`로 복사하고 `OPENAI_API_KEY` 값을 채운다. `.env.local`은 `.gitignore`로 제외되어 GitHub에 올라가지 않는다.

```powershell
Copy-Item .env.local.example .env.local
notepad .env.local
```

키 설정 후 실제 GPT 연결 테스트:

```powershell
C:\Users\lmhk2\anaconda3\Scripts\conda.exe run --no-capture-output -n stock_server_py311 python tools\openai_smoke_test.py
```

## 실행

권장 서버 환경:

```powershell
cd C:\Users\lmhk2\PycharmProjects\Stock_GPT_Analysis_Server1
C:\Users\lmhk2\anaconda3\Scripts\conda.exe create -y -n stock_server_py311 python=3.11
C:\Users\lmhk2\anaconda3\Scripts\conda.exe run --no-capture-output -n stock_server_py311 python -m pip install -r requirements.txt
C:\Users\lmhk2\anaconda3\Scripts\conda.exe run --no-capture-output -n stock_server_py311 python tools\runtime_check.py
```

Windows `py` launcher가 설치되어 있으면 `py -3.11 -m venv .venv`를 써도 된다.

오프라인 안정화 체크:

```powershell
C:\Users\lmhk2\anaconda3\Scripts\conda.exe run --no-capture-output -n stock_server_py311 python tools\stability_check.py
```

운영 준비 상태 전체 점검:

```powershell
C:\Users\lmhk2\anaconda3\Scripts\conda.exe run --no-capture-output -n stock_server_py311 python tools\ops_check.py
```

실제 OpenAI 호출까지 포함한 운영 점검:

```powershell
C:\Users\lmhk2\anaconda3\Scripts\conda.exe run --no-capture-output -n stock_server_py311 python tools\ops_check.py --live-openai
```

FastAPI 인증 smoke test:

```powershell
C:\Users\lmhk2\anaconda3\Scripts\conda.exe run --no-capture-output -n stock_server_py311 python tools\fastapi_smoke_test.py
```

관리자 대시보드 smoke test:

```powershell
C:\Users\lmhk2\anaconda3\Scripts\conda.exe run --no-capture-output -n stock_server_py311 python tools\admin_ui_smoke_test.py
```

환경변수 점검:

```powershell
C:\Users\lmhk2\anaconda3\Scripts\conda.exe run --no-capture-output -n stock_server_py311 python tools\env_check.py
```

DB migration 상태 점검:

```powershell
C:\Users\lmhk2\anaconda3\Scripts\conda.exe run --no-capture-output -n stock_server_py311 python tools\migration_check.py
```

SQLite DB 백업:

```powershell
C:\Users\lmhk2\anaconda3\Scripts\conda.exe run --no-capture-output -n stock_server_py311 python tools\backup_db.py
```

현재 환경에서 바로 실행 가능한 개발용 HTTP 서버:

```powershell
.\scripts\run_simple_server.ps1
```

개발용 서버 smoke test:

```powershell
C:\Users\lmhk2\anaconda3\Scripts\conda.exe run --no-capture-output -n stock_server_py311 python tools\server_smoke_test.py
```

FastAPI 정식 API 서버:

```powershell
.\scripts\run_fastapi_server.ps1
```

관리자 화면:

```text
http://127.0.0.1:8000/admin/ui
```

화면에서 `.env.local`의 `ADMIN_API_TOKEN`을 입력하면 사용자 목록, 요청 로그, GPT 호출 로그, 주문 요청, 사용자별 상세 정보를 조회할 수 있다. 토큰은 브라우저 `sessionStorage`에만 저장된다.

키움 OpenAPI+ legacy worker는 서버 본체와 분리해서 실행한다.

```powershell
.\scripts\run_kiwoom_legacy_worker.ps1
```

현재 `py37_32` 환경은 서버 본체가 아니라 키움 legacy 확인용으로만 사용한다.

## 복사/제외 원칙

재사용한 파일은 분석 로직 중심으로 제한했다. `.env`, `ticks.db`, `__pycache__`, `.idea`, 캡처 PNG, 임시 DB는 새 프로젝트에 복사하지 않았다.
