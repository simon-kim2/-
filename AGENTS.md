# Simon Trading Assistant

Korean stock trading assistant — safety-first AI orchestrator for personal stock trading on the Korea Investment Securities (KIS) platform.

## Cursor Cloud specific instructions

### Architecture

The codebase is structured across feature branches (main branch is minimal scaffold). Key branches:

- **NLU/routing branch** (`cursor/simon-routing-safety-scaffold-*`): Core NLU router, approval guards, intent classification, learning pipeline. Has `pyproject.toml` with `pythonpath = ["."]`.
- **Ops P0 branch** (`cursor/p0-ops-stabilization-*`): Operations server (stdlib `http.server`), dashboards, state management, watchdog.
- **Chat v2 branch** (`cursor/simon-chat-v2-control-bar-*`): Flask-based chat server, control bar UI, resident agent management.

### Running tests

```bash
# Branches with pyproject.toml (NLU branch):
pytest -v

# Branches without pyproject.toml (ops, chat):
PYTHONPATH=. pytest -v
```

### Running lint

```bash
ruff check .
```

### Running the server

Two server variants exist on different branches:

```bash
# Flask variant (chat v2 branch):
STOCK_SERVER_PORT=8080 STOCK_HOLD=true STOCK_READ_ONLY=true python3 server.py

# stdlib variant (ops P0 branch):
python3 server.py --port 8080
```

API endpoints:
- `GET /api/status` — server health and safety status
- `POST /api/chat` (ops branch) — send a text command; body: `{"message": "..."}`
- `GET /dashboard/wall` — main operations dashboard (HTML)
- `GET /chat` — chat interface (HTML)

### Key gotchas

- Python 3.11+ required (3.12 works fine).
- No database — all state is file-based JSON in `runtime/` directory.
- The `python` command is not available; always use `python3`.
- Branches without `pyproject.toml` need `PYTHONPATH=.` for imports to resolve.
- The ops server runs in `paper` mode by default with all safety guards active (HOLD=true, no broker connection). This is expected in dev — the system is designed to be safe-by-default.
- No Docker, no docker-compose needed.
- External dependencies (KIS broker API, Ollama/Qwen LLM, Whisper STT) are optional; the system runs in degraded/text-fallback mode without them.
