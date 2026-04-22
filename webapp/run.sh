#!/usr/bin/env bash
set -e

cd "$(dirname "$0")"
source .venv/bin/activate

export CONTROL_TOKEN="pool"

uvicorn app.main:app --host 0.0.0.0 --port 8000 --reload
