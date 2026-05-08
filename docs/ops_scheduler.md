# Simon operation loop separation

Simon keeps three loops separated so information collection cannot accidentally
become order execution.

## Trading engine loop

- `main.py` / `server.py`
- Handles broker state, chat IPC, account state, approvals, and order execution.
- Orders must pass `ApprovalGuard.verify_and_consume()`.

## sidongtv collection loop

- `tools/sidongtv_loop.py`
- Whitelisted channel only: `UCdwlSE2aW2VCCQIS5aJwTsA`
- Internal use only.
- Redistribution is prohibited.
- `advisory_only=true`.
- `order_trigger_allowed=false`.

Operating policy:

- 09:00-15:30 KST: collect only.
- 15:31-23:59 KST: collect plus internal preprocessing/summary.
- Night: learning input handoff only, separated from trading execution.

## Nightly learning loop

- `tools/pipeline_run.py --mode daily`
- Merges `data/curated/qa_intent_20000.jsonl` first.
- Keeps auto-promotion disabled.
- Model promotion requires manual approval and quality gates.
