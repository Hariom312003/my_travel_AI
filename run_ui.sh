#!/bin/bash
cd "$(dirname "$0")"

# In production (when PORT is defined or running in container), run using system streamlit if available
if [ -n "$PORT" ]; then
  echo "Production mode: running streamlit on port $PORT"
  if command -v streamlit >/dev/null 2>&1; then
    exec streamlit run app.py --server.port "$PORT" --server.address 0.0.0.0
  elif [ -x ".venv/bin/streamlit" ]; then
    exec .venv/bin/streamlit run app.py --server.port "$PORT" --server.address 0.0.0.0
  else
    exec python3 -m streamlit run app.py --server.port "$PORT" --server.address 0.0.0.0
  fi
else
  # Local development mode
  echo "Local development mode: running streamlit"
  if [ -x ".venv/bin/streamlit" ]; then
    exec .venv/bin/streamlit run app.py --server.port ${PORT:-8501} --server.address 0.0.0.0
  fi
  exec streamlit run app.py --server.port ${PORT:-8501} --server.address 0.0.0.0
fi
