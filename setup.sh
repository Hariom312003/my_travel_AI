#!/bin/bash
# Setup script for Multi-Agent AI Travel Assistant
set -e

echo "========================================="
echo "  Setting up Multi-Agent Travel Planner  "
echo "========================================="

# 1. Create virtual environment
if [ ! -d ".venv" ]; then
    echo "Creating virtual environment (.venv)..."
    python3 -m venv .venv
else
    echo "Virtual environment (.venv) already exists."
fi

# 2. Activate virtual environment
source .venv/bin/activate

# 3. Install dependencies
echo "Installing python dependencies from requirements.txt..."
pip install --upgrade pip
pip install -r requirements.txt

# 4. Ensure directories exist
mkdir -p memory/chroma_db
mkdir -p rag_data

# 5. Pre-ingest RAG data to local ChromaDB
echo "Initializing and pre-ingesting RAG travel database..."
python3 -c "
import sys
sys.path.insert(0, '.')
from agents.rag_agent import ingest_travel_data
try:
    ingest_travel_data()
    print('ChromaDB RAG Ingestion Complete!')
except Exception as e:
    print('Warning: Ingestion failed (will retry at runtime):', e)
"

echo "========================================="
echo "  Setup Completed Successfully!          "
echo "  To start the application, run: ./run.sh"
echo "========================================="
