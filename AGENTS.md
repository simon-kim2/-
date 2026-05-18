# AGENTS.md

## Cursor Cloud specific instructions

### Project overview

Simon Trading Assistant is a safety-first NLU routing scaffold for a Korean stock trading assistant. It is a **pure Python library/toolset** (Python >= 3.11) with no external runtime dependencies beyond the standard library. Dev dependencies are `pytest`, `ruff`, and `flask` (for the chat-v2 server branch).

### Important: main branch is empty

All code lives on feature branches. The `main` branch contains only a README. When working on this repo, check out the relevant feature branch first. Key code branches:

| Branch | Content |
|--------|---------|
| `cursor/dev-env-setup-313d` | NLU routing core, pyproject.toml, tests |
| `cursor/simon-routing-safety-scaffold-9e91` | Same NLU core (parallel branch) |
| `cursor/simon-chat-v2-control-bar-26d0` | Flask chat server, control bar UI |
| `cursor/resident-chat-sse-6d82` | Ops server (stdlib http.server), dashboards |
| `cursor/p0-ops-stabilization-6d82` | Ops stabilization (subset of above) |

### Quick reference

| Task | Command | Notes |
|------|---------|-------|
| Run tests (NLU core) | `pytest -v` | Works from repo root on branches with `pyproject.toml` |
| Run tests (other branches) | `PYTHONPATH=. pytest -v` | Branches without `pyproject.toml` need explicit `PYTHONPATH` |
| Lint | `ruff check .` | |
| Lint + fix | `ruff check --fix .` | |
| Start Flask chat server | `python3 server.py` | Port 18080 (on chat-v2 branch) |
| Start Ops server | `PYTHONPATH=. python3 server.py --port 18081` | On resident-chat-sse / p0-ops branch |

### Key constraints

- Python >= 3.11 is required (`StrEnum`, `datetime(UTC)`, `zoneinfo`).
- The NLU core has **zero** third-party runtime dependencies; all imports are stdlib.
- `flask>=3.0,<4` is needed only for the chat-v2 branch.
- `pyproject.toml` (on branches that have it) sets `pythonpath = ["."]` so tests resolve imports from the repo root.
- Branches without `pyproject.toml` require `PYTHONPATH=.` when running tests or the server.

### No external services required

No database, Docker, Redis, or external API is required for development. All state is file-based JSON. The KIS broker API integration is stubbed.
