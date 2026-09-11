# v0.1 구현 작업

## T1 — 일정 모델·설정·캐시
- Goal / Reason: 오프라인 표시와 안전한 설정 복원을 위한 기반 구현.
- Scope: models, repositories, settings; Google/GUI 제외.
- Acceptance Criteria: 종일 종료일 제외, 시간대 변환, 범위 캐시 교체, 실패 시 기존 캐시 유지, 잘못된 설정 복구.
- Tests: tests/test_core.py. RED → GREEN → 전체 회귀.
- Dependencies: 없음.

## T2 — Google 인증·동기화·Windows 서비스
- Goal / Reason: 서버 없이 읽기 전용 Google 연동 및 Windows 통합.
- Scope: OAuth, Credential Manager, API pagination, sync, startup, window geometry.
- Acceptance Criteria: 모든 페이지 성공 후 캐시 교체, 오류 시 캐시 보존, 토큰 파일 미생성, 자격 증명 자동 갱신, Run 등록/해제.
- Tests: tests/test_services.py (가짜 Google/자격증명으로 외부 계정 없이 검증).
- Dependencies: T1.

## T3 — 위젯·설정·트레이·배포
- Goal / Reason: 명세의 실제 사용자 흐름 제공.
- Scope: Qt UI, 비동기 작업, 진입점, 문서, PyInstaller.
- Acceptance Criteria: 월 이동/오늘/일정 표시, 이동·크기 복원, 설정, 로그인·로그아웃, 트레이, 오프라인 상태, 중복 실행 방지.
- Tests: tests/test_ui.py, offscreen 실행, lint/format/type check, EXE 빌드.
- Dependencies: T1, T2.
- 수동 검증: 실제 Google 동의·동기화, 재부팅 자동 실행, Explorer 재시작, Win+D, 모니터 변경은 실제 사용자 Windows 세션에서 확인 필요.
