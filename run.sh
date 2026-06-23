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

# Determine execution mode based on environment variables
PORT_VAL=${PORT:-8000}
SERVICE_NAME_LOWER=$(echo "$RAILWAY_SERVICE_NAME" | tr '[:upper:]' '[:lower:]')

if [ "$RUN_API" = "true" ] || [[ "$SERVICE_NAME_LOWER" == *"api"* ]] || [[ "$SERVICE_NAME_LOWER" == *"backend"* ]]; then
    echo "SRE Mode: Launching FastAPI Backend ONLY on port $PORT_VAL..."
    PORT=$PORT_VAL exec ./run_api.sh
elif [ "$RUN_UI" = "true" ] || [[ "$SERVICE_NAME_LOWER" == *"ui"* ]] || [[ "$SERVICE_NAME_LOWER" == *"frontend"* ]]; then
    echo "SRE Mode: Launching Streamlit Frontend ONLY on port $PORT_VAL..."
    PORT=$PORT_VAL exec ./run_ui.sh
else
    # Default: Run both concurrently for local development or combined deployment
    echo "Launching FastAPI Backend in background (port 8000)..."
    PORT=8000 ./run_api.sh &
    API_PID=$!

    sleep 3

    echo "Launching Streamlit Frontend in foreground (port 8501)..."
    PORT=8501 ./run_ui.sh

    # Cleanup background API process on exit
    echo "Stopping FastAPI Backend..."
    kill $API_PID 2>/dev/null || true
    echo "Done!"
fi
