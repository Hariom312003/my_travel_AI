#!/bin/bash
cd "$(dirname "$0")"
if [ -x ".venv/bin/uvicorn" ]; then
  exec .venv/bin/uvicorn src.api.app:app --host 0.0.0.0 --port ${PORT:-8000} --reload
fi
exec uvicorn src.api.app:app --host 0.0.0.0 --port ${PORT:-8000} --reload
