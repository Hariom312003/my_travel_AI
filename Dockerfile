FROM python:3.11-slim

# Set environment variables
ENV PYTHONUNBUFFERED=1 \
    PYTHONDONTWRITEBYTECODE=1 \
    ANONYMIZED_TELEMETRY=False

WORKDIR /app

# Install system dependencies
RUN apt-get update && apt-get install -y --no-install-recommends \
    build-essential \
    curl \
    && rm -rf /var/lib/apt/lists/*

# Install python packages
COPY requirements.txt .
RUN pip install --no-cache-dir --upgrade pip && \
    pip install --no-cache-dir -r requirements.txt

# Copy application files
COPY . .

# Ensure directory permissions and create necessary folders
RUN mkdir -p src/memory/chroma_db src/rag_data

# Run data ingestion to pre-populate ChromaDB
RUN python -c "import sys, os; sys.path.insert(0, os.path.abspath('src')); from rag.rag_agent import ingest_travel_data; ingest_travel_data()"

# Make scripts executable
RUN chmod +x run.sh run_api.sh run_ui.sh

# Default environment variables for container execution
ENV RUN_API=true
ENV PORT=8000
EXPOSE 8000

# Default command launches backend or frontend based on environment variables
CMD ["/bin/bash", "run.sh"]
