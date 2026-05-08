# AGENTS.md

## Cursor Cloud specific instructions

### Project overview

Simon Trading Assistant is a safety-first NLU routing scaffold for a Korean stock trading assistant. It is a **pure Python library/toolset** with no external runtime dependencies beyond the standard library. Dev dependencies are `pytest` and `ruff`.

### Quick reference

| Task | Command |
|------|---------|
| Run tests | `pytest -v` |
| Lint | `ruff check .` |
| Lint + fix | `ruff check --fix .` |
| Run sidongtv collector (single pass) | `python3 tools/sidongtv_loop.py --once` |
| Run daily learning pipeline | `python3 tools/pipeline_run.py --mode daily` |
| Build QA dataset | `python3 tools/build_qa_hardfail_dataset.py` |

### Key constraints

- Python >= 3.11 is required (`StrEnum`, `datetime(UTC)`, `zoneinfo`).
- The project has **zero** third-party runtime dependencies; all imports are stdlib.
- `pytest` and `ruff` are the only dev dependencies needed.
- `pyproject.toml` sets `pythonpath = ["."]` so tests and tools resolve imports from the repo root.
- Tools in `tools/` use `sys.path.insert(0, ...)` to ensure they work when run directly.

### No services to start

This is a library, not a web service. There is no dev server, database, or Docker dependency. All verification is done via `pytest` and running the CLI tools.
