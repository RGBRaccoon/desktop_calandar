# Project Rules

이 파일은 **이 프로젝트 전용 규칙**을 작성하는 곳이다.
중앙에서 배포되는 `AGENTS.md`와 `CLAUDE.md`는 직접 수정하지 않는다.

## Project Context

- 프로젝트 목적: Windows용 읽기 전용 Google Calendar 위젯.
- 주요 기술 스택: Python 3.12+, PySide6, SQLite, Windows Credential Manager.
- 주요 실행 명령: `.venv/Scripts/python -m desktop_calendar`

## Validation Commands

프로젝트에서 실제 사용하는 명령만 남긴다.

```bash
.venv/Scripts/python -m pytest -q
.venv/Scripts/python -m ruff check src tests scripts run.py
.venv/Scripts/python -m ruff format --check src tests scripts run.py
.venv/Scripts/python -m pyright
```

## Architecture Constraints

- UI는 Google API를 직접 호출하지 않는다. 네트워크 작업은 QThread에서 수행한다.
- CredentialStore는 Windows 백엔드만 사용한다. 토큰을 파일·DB·로그에 기록하지 않는다.
- 캐시는 모든 API 페이지 조회 성공 후 트랜잭션으로 교체한다.

## Additional Rules

- 실제 Google 계정 및 Windows 세션 테스트와 자동 테스트 결과를 구분한다.
- `scripts/validate.ps1`이 로컬/CI 공통 검증 명령이다. Windows CI는 QT_QPA_PLATFORM=windows 및 배율 1/1.5를 사용한다.
- 배포 EXE는 scripts/verify_executable.py로 창 복원·버튼·드래그·설정 및 저장을 검증한 후 제공한다.
