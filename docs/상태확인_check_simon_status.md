# check_simon_status.ps1 사용법 (한국어)

PC에 이미 있는 `scripts\check_simon_status.ps1` 로 **서버·Resident·대시보드** 를 한 번에 점검합니다.

## 실행

PowerShell:

```powershell
cd C:\주식ai\stock_trading
.\scripts\check_simon_status.ps1
```

대시보드까지 브라우저로 열기:

```powershell
.\scripts\check_simon_status.ps1 -OpenDashboard
```

## 포트 (중요)

이 스크립트는 **`http://127.0.0.1:8080`** 을 봅니다.

Resident / 채팅도 **같은 포트** 여야 합니다.

`config\local_simon.env` 에 넣기:

```text
STOCK_SERVER_PORT=8080
```

`start_simon_resident.bat` / `.ps1` 실행 전:

```bat
set STOCK_SERVER_PORT=8080
```

채팅 주소:

```
http://127.0.0.1:8080/chat_v2?session_id=resident_default&tts=1
```

(8080 대신 `/api/status` 가 열리는 포트를 쓰세요.)

## 결과 읽는 법

| 출력 | 의미 | 할 일 |
|------|------|--------|
| `NO_LISTENER` (8080) | 서버 꺼짐 | `start_simon_all.bat` 등으로 서버 시작 |
| `STATUS_HTTP=0` | `/api/status` 실패 | 서버·포트 확인 |
| `resident_pid_alive=false` | Resident 없음/죽음 | `start_simon_resident.ps1` |
| `resident_active=true` | Resident 동작 중 | 「사이먼」으로 말하기 |
| `RESIDENT_HTTP=0` | Resident API 실패 | `04` 에러 bat 또는 직접 python 실행 |

## Resident 실패와 포트

`resident_pid_not_alive_after_timeout` 인데 서버는 **8080** 만 열려 있으면, Resident가 **18080** 으로 붙으려다 실패할 수 있습니다. **반드시 포트 통일.**
