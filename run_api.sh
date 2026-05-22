#!/bin/bash
cd "$(dirname "$0")"
if [ -x ".venv/bin/uvicorn" ]; then
  exec .venv/bin/uvicorn api.app:app --host 0.0.0.0 --port 8000 --reload
fi
exec uvicorn api.app:app --host 0.0.0.0 --port 8000 --reload
