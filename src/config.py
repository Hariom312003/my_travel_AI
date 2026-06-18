"""Configuration management for the AI Travel Planner."""
import os
from dotenv import load_dotenv

# Load environment variables from .env
load_dotenv()

# General Environment
ENVIRONMENT = os.getenv("ENVIRONMENT", "production")

# LLM Configurations
MODEL_NAME = os.getenv("MODEL_NAME", "Qwen/Qwen2.5-7B-Instruct")
HF_TOKEN = os.getenv("HF_TOKEN") or os.getenv("HF_API_KEY")

# Local LLM (Ollama) Configurations
OLLAMA_URL = os.getenv("OLLAMA_URL", "http://localhost:11434")
USE_OLLAMA = os.getenv("USE_OLLAMA", "False").lower() in ("true", "1", "yes")

# Database Configuration
CHROMA_PATH = os.getenv("CHROMA_PATH", os.path.join(os.path.dirname(__file__), "memory/chroma_db"))

# Logging & Monitoring
LOG_LEVEL = os.getenv("LOG_LEVEL", "INFO")
MONITOR_LATENCY = os.getenv("MONITOR_LATENCY", "True").lower() in ("true", "1", "yes")
