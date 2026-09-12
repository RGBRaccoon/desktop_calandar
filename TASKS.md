# v0.1 구현 작업

## T7 — 트레이 복원 후 버튼 조작 시 창이 사라지는 오류
- Goal / Reason: 트레이 복원 및 자식 대화상자 조작 중 최하단 배치 방지.
- Scope: MainWindow의 지연 배치/활성화 처리 및 UI 회귀 테스트, 배포 EXE 갱신.
- Acceptance Criteria: 트레이 복원이 지연 배치를 취소하며 설정/일정 대화상자가 열려 있으면 부모를 내리지 않음. 비활성 일반 상태에서는 뒤로 배치.
- Tests: 트레이 복원/자식 대화상자/지연 실행 상태 재확인 회귀 테스트, 전체 검사 및 EXE smoke-test.
- Dependencies: T6.
- 검증: 트레이 복원/자식 대화상자 재현 테스트 2개 RED 확인 후 수정. 지연 실행 시 활성 상태 재확인 및 비활성 배치 포함 전체 29개 통과. Windows 네이티브 Qt에서도 해당 회귀 테스트 3개 통과. 수정 EXE는 release-fixed에 별도 제공.

## T6 — 인증 포함 단일 EXE 배포 빌드
- Goal / Reason: 앱 소유자가 제공한 Desktop OAuth 등록 설정을 포함한 독립 실행 파일 제공.
- Scope: Git 제외 리소스 설정, release spec 빌드, 아카이브/실행 검증 및 배포 상태 문서.
- Acceptance Criteria: 제공된 설정과 EXE 내 설정 일치, 단일 EXE 실행·정상 종료, 사용자 토큰 미포함.
- Tests: 전체 pytest 26개, Ruff lint/format, Pyright 통과. EXE 아카이브 설정 비교 통과. Windows smoke-test 종료 코드 0 및 화면 확인.
- Dependencies: T5 및 앱 소유자가 제공한 Desktop OAuth JSON.
- 결과: release/DesktopCalendar.exe 생성 완료. 실제 Google 로그인·권한 동의·Calendar API 접근은 사용자 계정에서 확인 필요.

## T5 — 배포용 Google 로그인 및 단일 EXE
- Goal / Reason: 최종 사용자가 OAuth JSON을 선택하지 않고 Google 로그인만 수행.
- Scope: 내장 Desktop OAuth 설정 탐색/검증, 설정 UI, onefile 배포 spec, 배포 안내.
- Acceptance Criteria: 내장 설정 자동 사용, JSON UI 제거, 잘못된/누락 설정은 로그인 전에 안내, 설정 없는 배포 빌드 차단.
- Tests: tests/test_distribution.py 및 전체 회귀/lint/format/type 검사.
- Dependencies: Google Cloud Desktop OAuth JSON은 앱 소유자가 발급해야 함. 현재 없음. 실제 인증 포함 EXE 생성과 계정 로그인은 파일 제공 후 검증.
- 검증: 미구현 모듈 RED → 26개 전체 테스트 통과. 누락 설정으로 release spec 실행 시 종료 코드 1로 빌드 차단 확인. 소스/UI 준비 완료, 실제 배포 EXE는 JSON 발급 대기.

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

## 검증 기록
- T1: 신규 테스트 수집 실패(미구현) 확인 → 모델/설정/캐시 구현 → 6개 통과.
- T2: 신규 서비스 미구현 실패 확인 → 인증/API/Windows 서비스 구현 → 누적 12개 통과.
- T3: UI 미구현 단계 검증 중 Qt 6.11 DLL 호환 실패 발견 → PySide6 6.8.3 고정 → UI/비동기 오류/월 이동/설정 테스트 통과.
- T4: 중복 이벤트 삽입 시 예외 미발생 RED 확인 → 복합 키·트랜잭션 구현 → 롤백/손상 복구/전체 캐시 삭제 통과.
- 전체: pytest 19개 통과, Ruff lint/format 및 Pyright 오류 없음.
- Windows 네이티브 창 생성, 일정 포함 화면, 설정 화면 렌더링 확인. PyInstaller EXE 빌드 및 smoke-test 정상 종료.
- 외부 확인 필요: 실제 Google 계정 동의·일정 조회, 재부팅 자동 실행, Explorer/절전/모니터 변경. 자격 증명과 사용자 로그인 없이 해당 항목은 완료로 표시하지 않음.

## T3 — 위젯·설정·트레이·배포
- Goal / Reason: 명세의 실제 사용자 흐름 제공.
- Scope: Qt UI, 비동기 작업, 진입점, 문서, PyInstaller.
- Acceptance Criteria: 월 이동/오늘/일정 표시, 이동·크기 복원, 설정, 로그인·로그아웃, 트레이, 오프라인 상태, 중복 실행 방지.
- Tests: tests/test_ui.py, offscreen 실행, lint/format/type check, EXE 빌드.
- Dependencies: T1, T2.
- 수동 검증: 실제 Google 동의·동기화, 재부팅 자동 실행, Explorer 재시작, Win+D, 모니터 변경은 실제 사용자 Windows 세션에서 확인 필요.

## T4 — 캐시 트랜잭션 검증
- Goal / Reason: 명세의 events 스키마와 일정 ID 중복 방지, 실패 시 원자적 복원 보장.
- Scope: EventRepository 및 저장 안전성 테스트.
- Acceptance Criteria: 범위·캘린더·일정 복합 키, 중복 삽입 실패 시 기존 데이터/동기화 시간 보존, 로그아웃 시 모든 범위 제거.
- Tests: tests/test_storage_safety.py; 중복 일정 테스트 RED 확인 후 정규화 스키마 구현.
- Dependencies: T1.
