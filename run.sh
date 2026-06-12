#!/bin/bash
# Startup script for Multi-Agent AI Travel Assistant

echo "========================================="
echo "  Starting Multi-Agent Travel Planner    "
echo "========================================="

# 1. Activate virtual environment
if [ -d ".venv" ]; then
    source .venv/bin/activate
fi

# 2. Make sure execution permissions are correct
chmod +x run_api.sh run_ui.sh

# 3. Start FastAPI server in the background
echo "Launching FastAPI Backend (port 8000)..."
./run_api.sh &
API_PID=$!

# 4. Wait for API to boot up
sleep 3

# 5. Start Streamlit UI in the foreground
echo "Launching Streamlit Frontend (port 8501)..."
./run_ui.sh

# 6. Cleanup background API process on exit
echo "Stopping FastAPI Backend..."
kill $API_PID 2>/dev/null || true
echo "Done!"
