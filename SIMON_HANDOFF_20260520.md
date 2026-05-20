# Simon 프로젝트 — 신규 Cursor 핸드오프 (2026-05-20)

> 이 문서는 긴 이전 세션(느려짐·컨텍스트 한도) 대신 **새 Cursor**가 바로 이어갈 수 있도록 정리한 것이다.  
> **실제 코드·로그·테스트는 사용자 로컬 Windows PC**에 있으며, 이 Git 워크스페이스(`/workspace`)에는 일부 지시서만 있을 수 있다.

---

## 1. 프로젝트 한 줄 요약

**Simon**: 로컬 주식 보조 AI (Flask `server.py`, Chat-v2 UI, NLU, KIS 연동 스켈레톤).  
**Qwen**: “감옥 LLM” — `FACT_BOX` 기반 설명·요약만, 주문·수치 조작·직접 브로커 제어 금지.  
**KIS**: 한국투자증권 API — 단계적 연동(읽기 전용 → 토큰/레이트리밋 → 실 HTTP는 게이트 뒤).  
**Resident**: 상시 마이크 VAD+STT 백그라운드 프로세스 — **현재 실험/로그 위주**, Chat-v2 오염 방지 기본 OFF.

---

## 2. 역할 분담 (반드시 유지)

| 역할 | 담당 | 할 일 |
|------|------|--------|
| 사용자 | 감독·최종 PASS | UI/음성/속도 체감, “된다/안 된다” 판정 |
| Cloud Cursor (이전 세션) | 목표·기준·지시서 | 아키텍처, 검증 기준, Local1/2 지시 |
| **Local Cursor 1** | 구현 | 코드·테스트·보고서 |
| **Local Cursor 2** | **독립 검증** | Local1이 한 일을 로그/API/UI로 재현·반박 |

**원칙**: Local1이 “PASS”라고 해도 Local2·사용자 확인 전까지 완료 아님.  
**금지**: “재시작하면 된다”, “이론상 된다”, 프로세스만 PASS하고 E2E FAIL로 닫기.

---

## 3. 아키텍처·안전 (절대 타협)

### 3.1 Simon
- NLU 라우터, SSOT(정규화된 시세·잔고), Safety Gate, 로깅.
- 기본: `HOLD`, read-only, `broker_submit=false`.
- 주문/자동매매: prepare → approval → safety gate → **사람 승인** 다단계.

### 3.2 Qwen
- Simon이 만든 `FACT_BOX`만 입력.
- 로그·UI·보고서·Qwen 입력에 `appkey`, `appsecret`, `access_token`, 계좌번호 **마스킹 필수**.

### 3.3 KIS
- 레이트리밋 준수 (예: REST 1~18 req/s, tokenP 1 req/s, WS 41 items/session).
- 캐시 TTL 정책.
- **실 HTTP / 실 토큰 요청은 환경 게이트 없이 금지**  
  예: `KIS_ALLOW_TOKEN_REQUEST=0`, `KIS_USE_REAL_HTTP=0` (스텁·목 단계).

### 3.4 Chat-v2 (`ui/chat_v2.html`)
- 운영자용 UI — 개발자 메타(`intent=`, `executed=` 등)는 기본 숨김(접기 “개발자 상세”).
- 버튼(예수금·전략 등): KIS 미연동 시 **1초 이내** “KIS 미연동 / 미확인” fast fallback (60초 블로킹 재발 금지).

### 3.5 Resident
- 기본: `SIMON_RESIDENT_CHAT_SEND_ENABLED=0` (Chat-v2로 자동 전송 OFF, 로그만).
- 브라우저 마이크(`source=voice`)와 Resident(`source=resident`) **경로 구분**하여 검증.
- Jabra: 운영 device **15** (48kHz), device 7 제외. 지시서: `resident_chatv2_delivery_20260518.md`.

### 3.6 TTS
- Edge `speechSynthesis`, 음성 우선순위: SunHi → HyunsuMultilingual → Heami.
- 긴 원문 대신 **`speak_text`** (코드·날짜·메타 제거, 숫자 자연어).

---

## 4. 개발 단계 (로드맵 요약)

문서 참고: `SIMON_최종목표와_개발순서.md`, `SIMON_QWEN_최종방향과구성.md`, `SIMON_현재문제와_해결과정.md` (로컬).

| Phase | 내용 | 상태(대략) |
|-------|------|------------|
| 0 | 브로커/실행 안전 골격 | 진행 중 (KIS 스켈레톤) |
| 1 | Chat-v2 기본 NLU·현재가·UI | 대부분 동작, 회귀 주의 |
| 2 | KIS read-only SSOT | 스켈레톤·목 테스트 다수 PASS |
| 3 | tokenP HTTP **계약 스텁** | Local1 구현 완료 → **Local2 검증 대기** |
| 4 | 실 KIS 연동 | 게이트 열기 전까지 금지 |
| 5 | NLU/LLM 학습 | **지금 본격 학습 X** — 데이터 Gold/Silver/Quarantine 분류 후 |

**학습 정책**: `data/curated` 대량 데이터(7만 건 언급)는 오염·비밀 스캔 후에만 사용. GPU 학습은 사용자가 “그만” 요청한 적 있음 — 감독 승인 없이 돌리지 말 것.

---

## 5. 직전 완료 작업 (Local1) — 검증 필요

### KIS tokenP HTTP client contract stub (2026-05-20)

**목적**: 실 네트워크 없이 tokenP 요청/응답 **계약·매핑·감사**만 검증.

**주요 파일 (로컬)**:
- `core/kis/http_client.py`
- `core/kis/token_manager.py`
- `core/kis/status_audit.py`
- `core/kis/__init__.py`
- `tests/test_kis_env_status_gates.py`
- `tests/fixtures/kis/tokenP_sample_ok.json`, `tokenP_sample_missing_field.json`
- `data/reports/kis_tokenP_contract_stub_20260520.md`

**Local1 주장**: 테스트 `33 passed, 1 skipped`; 비밀·raw token 미노출; `/api/status`에 토큰 관련 필드 반영; **실 HTTP 없음**.

**신규 Cursor / Local2가 할 일**:
1. 위 테스트를 **독립 실행** (`pytest tests/test_kis_env_status_gates.py` 등).
2. `KIS_ALLOW_TOKEN_REQUEST=0`, `KIS_USE_REAL_HTTP=0` 일 때 실제 HTTP가 나가지 않는지 확인.
3. 로그·status JSON에 `access_token` 원문 없는지 확인.
4. fixture 누락 필드 시 status/audit가 기대대로 `not_configured`/`error` 등인지 확인.
5. 결과를 `data/reports/`에 Local2 검증 보고서로 남김.

---

## 6. Resident E2E (아직 최우선 UX 중 하나)

**표준 발화**:
```
사이먼
삼성전자 현재가 알려줘
```

**PASS 5항목** (같은 턴 또는 연속 턴):
1. VAD `vad_detected=true` (또는 재시도 후 transcript)
2. `resident_events.jsonl`: `transcript_sent`, `sent_to_server=true`
3. `chat_v2_messages.jsonl`: `session_id=resident_default`, `source=resident`, user+assistant
4. `tts_spoken ok=true`
5. UI `.../chat_v2?session_id=resident_default&tts=1` 동일 답변

상세: `/workspace/resident_chatv2_delivery_20260518.md`

**알려진 함정**:
- 포트 **8080** vs **18080** — 구 서버 PID 잔존 시 코드 불일치; status의 `server_pid`·port 확인.
- wake 미제거 → “종목을 찾지 못했습니다”; `사이먼.` / `사이몬` / `세임 on` 등 STT 변형 → fuzzy wake + `strip_leading_wake_words` (resident + server 이중).
- `no_audio`를 fatal로 처리하지 말 것; VAD 재시도·listen window 8초+.
- Resident가 Chat에 쏘면 voice 테스트 오염 → 기본 chat send OFF 유지.

---

## 7. 이미 고친 것 (회귀 시 재확인)

| 증상 | 원인 | 조치 |
|------|------|------|
| 채팅 무응답 | session/polling, NLU | session 고정, 라우팅 수정 |
| 예수금/전략 60초 | KIS/IPC 블로킹 | fast fallback |
| TTS 로봇/느림 | SunHi 없음, 원문 읽기 | voice fallback chain, `speak_text` |
| UI 지저분 | dev 메타 노출 | 접기 섹션 |
| git_hash=unknown | git PATH/.git | `data/build_info.json` |
| 브라우저 마이크 network | Edge Web Speech 외부 | Simon 서버 이슈 아님 — Edge/온라인 음성 설정 |

---

## 8. 검증에 쓸 증거 (로컬 경로)

- `data/logs/chat_v2_messages.jsonl`
- `data/logs/resident_events.jsonl`
- `data/logs/chat_latency.jsonl`
- `GET /api/status`, `GET /api/resident/status`
- `POST /api/chat/send` (body에 session_id, text)

**응답에 항상 확인**: `executed=false`, `broker_submit=false` (조회·설명 경로).

---

## 9. 운영 환경

- **OS**: Windows, i9-14900K, RTX 3090
- **서버**: Python Flask, 기본 포트 **8080** 권장
- **Resident 시작**: `scripts/start_simon_resident.bat`
- **진단**: `tools/resident_health_check.py`
- **KIS**: 사용자가 rate limit·OAuth·보안 정책 숙지; symbol master는 `tools/fetch_kis_symbol_master.py` 등 (수동/반자동 가능)

---

## 10. 신규 Cursor에게 당장 할 일 (우선순위)

1. **Local2**: KIS tokenP contract stub 독립 검증 → 보고서.
2. **회귀 방지**: Chat-v2 “삼성전자 현재가”, “예수금” 버튼 **3초 이내** 체감 재확인.
3. **Resident**: chat send OFF 유지한 채, 표준 발화 E2E 5항목 (사용자 PC).
4. **KIS 다음 스텝**: tokenP 스텁 PASS 후 → live HTTP는 게이트·체크리스트·onboarding 문서 따라 **한 단계씩**.
5. **학습/GPU**: 감독 명시 전까지 본격 학습·GPU 부하 작업 금지.
6. **세션 성능**: 지시는 **짧은 단위**로; 긴 대화는 새 채팅 + 이 핸드오프 링크.

---

## 11. 지시문 톤 (사용자 요청)

- “검증 회피” 뉘앙스 금지 → **기술 요구는 엄격**, 말투는 협조적.
- 사용자 불만: “진단만 하고 안 고침” → **채팅창 전 기능이 학습 전에도 동작**해야 함.
- 신뢰: 수정마다 회귀 만들지 말 것; PASS는 로그·UI·체감으로만.

---

## 12. 이 리포지토리(`/workspace`) 현황

- `resident_chatv2_delivery_20260518.md` — Resident E2E 지시서
- `SIMON_HANDOFF_20260520.md` — 본 문서
- 전체 Simon 소스는 **로컬 클론**이 SSOT — 브랜치 예: `cursor/resident-e2e-deliverable-393e`, `main`, 기타 `cursor/simon-*`

---

## 13. 첫 메시지 템플릿 (신규 Cursor에 붙여넣기)

```
Simon 로컬 프로젝트 이어갑니다. 핸드오프: SIMON_HANDOFF_20260520.md

역할: Local2 검증자. Local1이 완료한 KIS tokenP HTTP contract stub을 독립 검증해 주세요.
- KIS_ALLOW_TOKEN_REQUEST=0, KIS_USE_REAL_HTTP=0 유지
- pytest 및 /api/status, 로그에 secret/raw token 없음 확인
- 결과 data/reports/에 보고

그 다음 Chat-v2 회귀(삼성전자 현재가, 예수금 버튼 속도)만 짧게 확인해 주세요.
Resident E2E는 사용자 PC에서만; SIMON_RESIDENT_CHAT_SEND_ENABLED=0 유지.
```

---

*문서 작성: Cloud Agent handoff, 2026-05-20*
