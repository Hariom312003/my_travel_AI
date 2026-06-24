#!/bin/bash
cd "$(dirname "$0")"

# In production (when PORT is defined or running in container), run without reload
if [ -n "$PORT" ]; then
  echo "Production mode: running uvicorn without reload on port $PORT"
  # Try system uvicorn first, then local venv if system is not found
  if command -v uvicorn >/dev/null 2>&1; then
    exec uvicorn src.api.app:app --host 0.0.0.0 --port "$PORT"
  elif [ -x ".venv/bin/uvicorn" ]; then
    exec .venv/bin/uvicorn src.api.app:app --host 0.0.0.0 --port "$PORT"
  else
    exec python3 -m uvicorn src.api.app:app --host 0.0.0.0 --port "$PORT"
  fi
else
  # Local development mode
  echo "Local development mode: running uvicorn with reload"
  if [ -x ".venv/bin/uvicorn" ]; then
    exec .venv/bin/uvicorn src.api.app:app --host 0.0.0.0 --port ${PORT:-8000} --reload
  fi
  exec uvicorn src.api.app:app --host 0.0.0.0 --port ${PORT:-8000} --reload
fi
