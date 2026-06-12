FROM python:3.10-slim

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
RUN mkdir -p memory/chroma_db rag_data

# Run data ingestion to pre-populate ChromaDB
RUN python -c "import sys; sys.path.insert(0, '.'); from agents.rag_agent import ingest_travel_data; ingest_travel_data()"

# Expose ports
EXPOSE 8000
EXPOSE 8501

# Default command
CMD ["python", "main.py"]
