# Desktop Calendar v0.1

Windows 10/11용 Google Calendar 읽기 전용 바탕화면 위젯입니다. 별도 중계 서버 없이 Google API에 직접 연결합니다.

## 실행

배포 빌드는 `release/DesktopCalendar.exe` 하나로 실행합니다. Python 설치가 필요하지 않습니다. 시작할 때 내부 라이브러리를 임시 폴더에 풀기 때문에 첫 실행은 잠시 걸릴 수 있습니다.

**현재 배포 상태:** 앱 소유자의 OAuth JSON이 아직 없어 인증 포함 배포 EXE는 생성하지 않았습니다. 기존 `dist/DesktopCalendar/DesktopCalendar.exe`는 이전 개발 빌드로, JSON을 직접 선택하는 화면이 남아 있습니다.

소스 실행 (PowerShell, 프로젝트 폴더):

```powershell
python -m venv .venv
.venv/Scripts/python -m pip install -e '.[dev]'
.venv/Scripts/python -m desktop_calendar
```

설치 후 `launch.cmd`로 콘솔 없이 실행할 수 있습니다. Python 3.12 이상이 필요하며 이 PC에서는 Python 3.13.9 / PySide6 6.8.3으로 검증했습니다. PySide6는 검증된 버전으로 고정했습니다.

## 사용자 Google 연결

배포 EXE에서 **설정 → Google 로그인 / 계정 변경**을 누르고, 브라우저에서 Google 로그인과 Calendar 읽기 권한 동의를 완료하면 됩니다. 사용자에게 JSON 파일을 요구하지 않습니다.

## 배포자가 한 번 할 설정

1. [Google Cloud Console](https://console.cloud.google.com/)에서 프로젝트를 만들고 **Google Calendar API**를 활성화합니다.
2. Google Auth Platform에서 동의 화면을 구성합니다. 개인 테스트 앱은 본인 계정을 테스트 사용자에 추가합니다.
3. OAuth 클라이언트를 **데스크톱 앱** 유형으로 생성하고 JSON을 다운로드합니다.
4. JSON을 `src/desktop_calendar/resources/oauth_client.json`으로 저장합니다. Git에서는 제외됩니다.
5. 아래 명령으로 인증 설정을 포함하는 단일 EXE를 만듭니다.

```powershell
.venv/Scripts/python -m PyInstaller --noconfirm --distpath release DesktopCalendar-release.spec
```

클라이언트 설정이 없거나 웹/서비스 계정 유형이면 빌드를 중단합니다. 개인 Google 계정은 동의 화면의 대상 사용자를 External로 구성하고, 테스트 단계에서는 본인 이메일을 테스트 사용자에 추가하세요. 불특정 사용자에게 공개할 때는 배포 상태와 요청 권한에 따른 Google 검증 절차를 별도로 완료해야 할 수 있습니다. [Google 공식 등록 안내](https://developers.google.com/workspace/calendar/api/quickstart/python), [공개 앱 권한 검증](https://developers.google.com/identity/protocols/oauth2/production-readiness/sensitive-scope-verification).

데스크톱 OAuth 앱 등록 정보는 EXE에 포함합니다. 데스크톱 앱은 클라이언트 설정을 숨길 수 없는 public client이며 PKCE와 시스템 브라우저를 사용합니다. 사용자 OAuth 토큰은 배포 파일·SQLite·로그에 저장하지 않습니다. `keyring`의 Windows 백엔드를 명시하여 **Windows 자격 증명 관리자 / DesktopCalendar / google_oauth_token**에만 저장합니다. 인증 콜백에는 로그인 중에만 동작하는 PC 내부 loopback 주소를 사용합니다.

액세스 토큰은 자동 갱신하며 갱신 권한이 취소되면 재로그인을 안내합니다. 테스트 모드 앱의 인증 수명 등 Google 정책은 [데스크톱 OAuth 공식 문서](https://developers.google.com/identity/protocols/oauth2/native-app)를 확인하세요. 로그인 브라우저를 닫으면 최대 2분 후 대기가 끝납니다.

## 사용 방법

- 상단 글자를 끌어 이동하고 우측 아래 손잡이로 크기를 조절합니다.
- `‹` / `›`로 월 이동, **오늘**로 현재 월 이동, `↻`로 새로고침합니다.
- 날짜를 클릭하면 생략된 일정을 포함한 해당 날짜의 목록을 확인합니다.
- 설정에서 테마, 배경색, 창 투명도, 글자 크기, 표시 개수, 시작 요일, 동기화 주기, Windows 자동 실행을 변경합니다.
- 창 닫기는 트레이로 숨기며 **트레이 → 종료**로 종료합니다. 창 우클릭 메뉴에서도 설정·종료가 가능합니다.
- 일반 창 뒤로 배치하며 WorkerW에 삽입하지 않습니다. Win+D로 숨겨진 경우 트레이의 **달력 표시**로 복원합니다. 모든 Windows 상태에서 바탕화면에 계속 표시되는 Explorer 내장 위젯 방식은 아닙니다.
- 오프라인에서는 이전에 조회한 동일 날짜 범위·캘린더 선택의 캐시를 표시합니다. 처음 방문한 달은 비어 있을 수 있습니다.
- 로그아웃은 이 PC의 자격 증명과 모든 일정 캐시를 제거합니다. Google 계정 자체의 앱 접근 권한까지 철회하려면 Google 계정의 연결된 앱 관리에서 제거하세요.

## 구현

`src/desktop_calendar` 아래에 UI / services / repositories / models / infrastructure를 분리했습니다.

- 월간 42칸 그리드, 오늘 강조, 날짜별 일정 및 초과 개수, 캘린더 색상.
- 반복 일정은 Google `singleEvents`로 펼치고 모든 페이지를 조회합니다. 종일 종료일은 제외하고 시간 일정은 PC 시간대로 표시합니다.
- 화면의 앞뒤 달 날짜까지 조회합니다. 전체 캘린더·페이지 성공 후 SQLite 트랜잭션으로 범위를 교체하여 삭제·취소 일정을 제거합니다.
- `events` 테이블의 범위·캘린더·일정 복합 키로 중복을 방지하며 동기화 시간을 별도 보관합니다.
- QThread에서 네트워크 작업을 수행하고 Qt signal로 화면을 갱신합니다. 진행 중 요청은 합쳐 처리합니다.
- 위치·크기 저장, 사라진 모니터에서 주 모니터로 복구, HKCU Run 자동 실행, 중복 실행 방지.
- DB 손상은 손상 파일을 보존한 뒤 재생성합니다. 잠금·일반 I/O 오류에 DB를 삭제하지 않습니다.

저장 경로:

```text
%APPDATA%/DesktopCalendar/config.json
%LOCALAPPDATA%/DesktopCalendar/calendar.db
%LOCALAPPDATA%/DesktopCalendar/logs/app.log
```

로그는 파일당 1MB, 이전 3개까지 순환합니다. 일정 제목·본문·토큰·Authorization 헤더·HTTP 예외 본문은 기록하지 않습니다. 일정 캐시는 로컬 SQLite 평문이므로 PC 사용자 계정 접근 권한을 따릅니다.

## 검증·빌드

```powershell
.venv/Scripts/python -m pytest -q
.venv/Scripts/python -m ruff check src tests run.py
.venv/Scripts/python -m ruff format --check src tests run.py
.venv/Scripts/python -m pyright
.venv/Scripts/python -m desktop_calendar --smoke-test --data-dir .local/smoke --screenshot .local/smoke.png
.venv/Scripts/python -m PyInstaller --noconfirm DesktopCalendar.spec
```

`--smoke-test`는 Google 연결 없이 창을 생성하고 자동 종료합니다. `--data-dir`로 일반 사용자 데이터와 분리합니다. 자동 테스트에서는 자격 증명·Google API를 대역으로 검증하고 실제 계정 로그인이나 Run 레지스트리를 변경하지 않습니다.

실제 Google OAuth 동의·동기화, 재부팅 자동 실행, Explorer 재시작, 절전 복귀, 모니터 연결/해제, Win+D는 실제 사용자 세션에서 최종 확인해야 합니다. 일정 생성·수정·삭제·알림은 v0.1에 포함하지 않습니다.

API 구현 참고: [Google events.list](https://developers.google.com/workspace/calendar/api/v3/reference/events/list), [Qt QThread](https://doc.qt.io/qtforpython-6/PySide6/QtCore/QThread.html), [Qt System Tray](https://doc.qt.io/qtforpython-6/PySide6/QtWidgets/QSystemTrayIcon.html).
