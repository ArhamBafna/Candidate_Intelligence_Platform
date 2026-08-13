import logging
import structlog
import sys
from collections import deque
import threading

LOG_BUFFER = deque(maxlen=100)
_buffer_lock = threading.Lock()

def memory_buffer_processor(logger, method_name, event_dict):
    with _buffer_lock:
        LOG_BUFFER.appendleft(dict(event_dict))
    return event_dict

def get_recent_logs(limit: int = 50):
    with _buffer_lock:
        return list(LOG_BUFFER)[:limit]

def setup_logging():
    structlog.configure(
        processors=[
            structlog.contextvars.merge_contextvars,
            structlog.processors.add_log_level,
            structlog.processors.TimeStamper(fmt="iso"),
            memory_buffer_processor,
            structlog.processors.JSONRenderer()
        ],
        wrapper_class=structlog.make_filtering_bound_logger(logging.INFO),
        context_class=dict,
        logger_factory=structlog.PrintLoggerFactory(sys.stdout),
        cache_logger_on_first_use=True
    )

