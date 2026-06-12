# Deployment & Configuration Manual

This document guides the installation, environment configuration, and containerized deployment of the **my_travel_AI** platform.

---

## 1. Environment Configurations (`.env`)
Create a `.env` file in the root of the project. The configuration parameters are:

| Key | Default | Description |
| :--- | :--- | :--- |
| `ENVIRONMENT` | `production` | Active running mode (`production` or `development`). |
| `MODEL_NAME` | `Qwen/Qwen2.5-7B-Instruct` | Target Hugging Face Instruct model. |
| `HF_TOKEN` | *None* | Hugging Face Hub User Access Token. |
| `USE_OLLAMA` | `False` | Toggle to route to local Ollama server instead. |
| `OLLAMA_URL` | `http://localhost:11434` | Target endpoint for local Ollama server. |
| `CHROMA_PATH` | `memory/chroma_db` | Persistent database storage path. |
| `MONITOR_LATENCY` | `True` | Trace and record agent latency inside logs. |

---

## 2. Local Installation (Python Setup)

### Prerequisites
* Python 3.10 to 3.12 installed.
* Virtualenv utility.

### Setup Steps
1. **Bootstrap the environment**:
   ```bash
   ./setup.sh
   ```
   This script creates a virtual environment, upgrades pip, installs `requirements.txt` dependencies, and initializes configuration variables.
2. **Activate the environment**:
   ```bash
   source .venv/bin/activate
   ```
3. **Execute the validation tests**:
   ```bash
   python3 -m unittest test_suite.py
   ```

---

## 3. Running Services Locally

Start the backend API and the frontend dashboard:
```bash
./run.sh
```
This launches:
1. **FastAPI Backend Router** on port `8000` via Uvicorn.
2. **Streamlit UI Client** on port `8501`.

---

## 4. Container Deployment (Docker)

Ensure **Docker** and **Docker Compose** are installed.

### Service Orchestration
The deployment architecture is declared in `docker-compose.yml`:
```yaml
version: '3.8'

services:
  api:
    build: .
    ports:
      - "8000:8000"
    environment:
      - ENVIRONMENT=production
      - HF_TOKEN=${HF_TOKEN}
      - USE_OLLAMA=${USE_OLLAMA}
    volumes:
      - ./memory:/app/memory

  ui:
    build: .
    command: streamlit run ui/streamlit_app.py --server.port=8501 --server.address=0.0.0.0
    ports:
      - "8501:8501"
    environment:
      - API_URL=http://api:8000
    depends_on:
      - api
```

### Launch Commands
* **Start all containers**:
   ```bash
   docker-compose up --build
   ```
* **Stop services**:
   ```bash
   docker-compose down
   ```
