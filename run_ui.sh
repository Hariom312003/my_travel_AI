#!/bin/bash
cd "$(dirname "$0")"
if [ -x ".venv/bin/streamlit" ]; then
  exec .venv/bin/streamlit run app.py --server.port ${PORT:-8501} --server.address 0.0.0.0
fi
exec streamlit run app.py --server.port ${PORT:-8501} --server.address 0.0.0.0
