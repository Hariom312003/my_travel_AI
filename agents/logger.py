"""Structured Logger and Latency Monitoring for Multi-Agent Planner."""
import time
import uuid
import logging
import json
import sys
from contextlib import contextmanager
from typing import Generator

import contextvars
import os

# Thread/Async-safe context-local request ID
_request_id_var = contextvars.ContextVar("request_id", default=None)

def get_request_id() -> str:
    """Get the current request ID or generate a new one."""
    req_id = _request_id_var.get()
    if not req_id:
        req_id = str(uuid.uuid4().hex[:8])
        _request_id_var.set(req_id)
    return req_id

def set_request_id(request_id: str) -> None:
    _request_id_var.set(request_id)

def clear_request_id() -> None:
    _request_id_var.set(None)

# Custom JSON Log Formatter
class JsonFormatter(logging.Formatter):
    def format(self, record: logging.LogRecord) -> str:
        log_payload = {
            "timestamp": self.formatTime(record, "%Y-%m-%d %H:%M:%S"),
            "level": record.levelname,
            "logger": record.name,
            "message": record.getMessage(),
            "request_id": get_request_id()
        }
        if hasattr(record, "latency_ms"):
            log_payload["latency_ms"] = record.latency_ms
        if record.exc_info:
            log_payload["exception"] = self.formatException(record.exc_info)
        return json.dumps(log_payload)

# Initialize global logger
logger = logging.getLogger("travel_assistant")
logger.setLevel(logging.INFO)

# 1. Console Stream Handler
handler = logging.StreamHandler(sys.stdout)
handler.setFormatter(JsonFormatter())
logger.addHandler(handler)

# 2. Shared File Handler (for live tailing in UI)
log_dir = os.path.abspath(os.path.join(os.path.dirname(__file__), "../memory"))
os.makedirs(log_dir, exist_ok=True)
log_file = os.path.join(log_dir, "app.log")
file_handler = logging.FileHandler(log_file, encoding="utf-8")
file_handler.setFormatter(JsonFormatter())
logger.addHandler(file_handler)

@contextmanager
def monitor_agent(agent_name: str) -> Generator[str, None, None]:
    """Context manager to measure latency and log execution events in structured JSON."""
    req_id = get_request_id()
    start_time = time.time()
    
    logger.info(f"Starting agent: {agent_name}")
    try:
        yield req_id
        duration_ms = (time.time() - start_time) * 1000
        
        # Log success with latency
        extra = {"latency_ms": round(duration_ms, 2)}
        record = logger.makeRecord(
            name=logger.name,
            level=logging.INFO,
            fn="",
            lno=0,
            msg=f"Successfully completed agent: {agent_name}",
            args=(),
            exc_info=None,
            extra=extra
        )
        logger.handle(record)
    except Exception as e:
        duration_ms = (time.time() - start_time) * 1000
        logger.error(
            f"Error during agent: {agent_name} - {str(e)}",
            exc_info=True,
            extra={"latency_ms": round(duration_ms, 2)}
        )
        raise e
