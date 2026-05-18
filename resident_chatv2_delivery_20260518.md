# Resident -> Chat-v2 -> TTS 즉시 결과물 지시서 (2026-05-18)

## 결론

이번 묶음은 "프로세스 PASS / E2E FAIL"로 닫지 않는다. 로컬 Cursor는 아래 수정까지 반영하고,
사용자 PC에서 한 번의 표준 발화가 Chat-v2 답변과 TTS까지 이어지는 것을 증거로 남긴다.

표준 발화:

```text
사이먼
삼성전자 현재가 알려줘
```

표준 URL:

```text
http://127.0.0.1:18080/chat_v2?session_id=resident_default&tts=1
```

## 지금 반영할 코드/스크립트 변경

### 1. Resident 장치 기본값 고정

`scripts/start_simon_resident.bat`에서 운영 기본값을 무조건 device 15로 둔다.

```bat
set "SIMON_RESIDENT_DEVICE_INDEX=15"
set "SIMON_STT_DEVICE_INDEX=15"
set "SIMON_RESIDENT_SAMPLE_RATE=48000"
set "SIMON_STT_SAMPLE_RATE=48000"
```

device 7은 제외한다. device 1은 후보로만 남긴다.

### 2. `/restart` PID 판정 개선

Whisper 로딩 때문에 12~20초 사이 PID가 늦게 생긴다. `/restart` 직후 실패처럼 보이지 않게 한다.

필수 동작:

- stale pid 파일 삭제
- start 실행
- 최소 30초까지 pid 파일 생성 및 process alive 확인
- pid 생성 전에는 실패가 아니라 `starting=true`, `phase=loading_model`로 표시
- 30초 후에도 pid/process가 없을 때만 실패

### 3. VAD no-audio 한 번으로 버리지 않기

현재 device 15에서 `peak=0.0064 < 0.05`로 `vad_no_audio`가 찍히면 바로 전송이 멈춘다.
Resident는 한 번의 no-audio로 턴을 버리지 말고 짧은 재수집을 해야 한다.

필수 동작:

- wake 대기 중 `vad_no_audio`가 나오면 2~3회 재시도
- 각 재시도는 2초보다 길게, 최소 4초 수집
- 전체 wake listen window는 8초 이상
- 재시도 로그에 `vad_retry_index`, `observed_rms`, `observed_peak` 기록

### 4. STT timeout 2초 고정 해제

`stt_timeout_after_2.0s`가 반복된다. 기본 timeout을 6초로 올린다.

필수 환경값:

```bat
set "SIMON_STT_TIMEOUT_SEC=6"
set "SIMON_RESIDENT_LISTEN_WINDOW_SEC=8"
```

코드가 이 환경값을 읽지 않으면 Resident 코드에 반영한다.

### 5. wake word 처리 수정

STT가 `사이먼 현재가 알려줘`, `사이먼 사이먼 현재가 알려줘`, `사이마 삼성전자 현재가 알려줘`를 그대로 서버에 보내면 안 된다.

필수 동작:

- wake 후보: `사이먼`, `사이먼아`, `사이마`, `사이면`, `simon`
- 문장 앞의 wake 후보는 서버 전송 전에 제거
- wake만 들리면 `wake_active=true` 상태를 8초 유지
- wake 이후 다음 transcript는 wake가 없어도 서버로 전송
- wake 제거 후 본문이 비면 `/api/chat/send`로 보내지 않음

예:

```text
raw: 사이마 삼성전자 현재가 알려줘
send_text: 삼성전자 현재가 알려줘
```

```text
raw: 사이먼 현재가 알려줘
send_text: 현재가 알려줘
```

이 경우 서버는 직전 종목 context가 없으면 "어떤 종목의 현재가를 볼까요?"로 답해야 한다.

### 6. 서버 방어 정제 추가

Resident에서 제거하지 못해도 `server.py` Chat-v2 경로에서 한 번 더 정제한다.

적용 위치:

- `/api/chat/send`에서 `_incoming_chat_text()` 직후
- 또는 `merge_routing_decision()` 전에

필수 함수:

```python
def strip_leading_wake_words(text: str) -> str:
    # 문장 앞 wake word 반복 제거
    # "사이먼 사이먼 삼성전자 현재가 알려줘" -> "삼성전자 현재가 알려줘"
    ...
```

단, wake word 단독 발화는 기존 assistant_wake 응답을 유지한다.

### 7. 종목 없는 현재가 질문 처리

`현재가 알려줘`처럼 종목이 빠진 질문은 종목 검색 실패로 보내지 말고 clarification으로 보낸다.

응답:

```text
어떤 종목의 현재가를 볼까요?
종목명 또는 종목코드를 말해 주세요.
주문은 실행하지 않았습니다.
intent=price_lookup_clarification
executed=false
broker_submit=false
```

## PASS 기준

아래 5개가 같은 턴 또는 연속 턴에서 확인되어야 한다.

| # | 항목 | PASS 조건 |
|---|------|-----------|
| 1 | VAD | `vad_detected=true` 또는 재시도 후 transcript 생성 |
| 2 | 전송 | `resident_events.jsonl`에 `transcript_sent`, `sent_to_server=true` |
| 3 | Chat-v2 | `chat_v2_messages.jsonl`에 `session_id=resident_default`, `source=resident`, user+assistant 쌍 |
| 4 | TTS | `resident_events.jsonl`에 `tts_spoken ok=true` |
| 5 | UI | `resident_default&tts=1` 화면에 동일 답변 표시 |

`source=voice`는 브라우저 마이크 경로이므로 Resident PASS가 아니다.

## 테스트 케이스

### A. 정상 가격 조회

발화:

```text
사이먼
삼성전자 현재가 알려줘
```

기대:

- 서버 전송 text: `삼성전자 현재가 알려줘`
- intent: `price_lookup`
- symbol_code: `005930`
- 주문 실행 없음
- TTS: 삼성전자 가격 발화

### B. wake 포함 한 문장

발화:

```text
사이먼 삼성전자 현재가 알려줘
```

기대:

- 서버 전송 text: `삼성전자 현재가 알려줘`
- 결과는 A와 동일

### C. 종목 없는 현재가

발화:

```text
사이먼 현재가 알려줘
```

기대:

- 종목 검색 실패가 아니라 clarification
- 주문 실행 없음

### D. 반복 wake

발화:

```text
사이먼 사이먼 삼성전자 현재가 알려줘
```

기대:

- 서버 전송 text: `삼성전자 현재가 알려줘`
- 결과는 A와 동일

## 보고서 형식

최종 보고서는 `data/reports/resident_chatv2_unified_20260518.md`에 갱신한다.

반드시 포함:

- Resident PID
- `/api/status.resident_pid_alive`
- `/api/resident/status.device_index`
- raw transcript
- cleaned send_text
- `wake_detected`
- `transcript_sent`
- Chat-v2 user/assistant JSONL 행
- `tts_spoken`
- UI 표시 여부

## 최종 운영값

```bat
set "SIMON_RESIDENT_DEVICE_INDEX=15"
set "SIMON_STT_DEVICE_INDEX=15"
set "SIMON_RESIDENT_SAMPLE_RATE=48000"
set "SIMON_STT_SAMPLE_RATE=48000"
set "SIMON_STT_TIMEOUT_SEC=6"
set "SIMON_RESIDENT_LISTEN_WINDOW_SEC=8"
```

이 결과물의 목적은 후속 이슈를 만드는 것이 아니라, 현재 Resident 상시 음성이 최소한 삼성전자 현재가 질문에 답하도록 만드는 것이다.
