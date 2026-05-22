#!/bin/bash
cd "$(dirname "$0")"
if [ -x ".venv/bin/streamlit" ]; then
  exec .venv/bin/streamlit run ui/streamlit_app.py --server.port 8501 --server.address 0.0.0.0
fi
exec streamlit run ui/streamlit_app.py --server.port 8501 --server.address 0.0.0.0
