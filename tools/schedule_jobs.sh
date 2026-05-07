#!/usr/bin/env bash
set -euo pipefail

# Keep operating loops separate:
# - main.py/server.py: trading engine and chat UI
# - sidongtv_loop.py: sidongtv internal advisory collection only
# - pipeline_run.py: daily learning pipeline with HOLD/no auto-promotion

python tools/sidongtv_loop.py --once
python tools/pipeline_run.py --mode daily
