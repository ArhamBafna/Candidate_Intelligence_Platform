import pytest
import structlog
from config.logging import setup_logging

def test_setup_logging_configures_structlog():
    # Call the setup
    setup_logging()
    
    # Assert structlog is configured
    assert structlog.is_configured()
    
    # Assert we can get a logger and bind to it
    logger = structlog.get_logger()
    logger = logger.bind(test_key="test_value")
    # This shouldn't throw an error, verifying the basic config is sane

def test_get_recent_logs_truncation():
    from config.logging import LOG_BUFFER, get_recent_logs
    LOG_BUFFER.clear()
    for i in range(10):
        LOG_BUFFER.appendleft({"msg": f"log {i}"})
    
    logs = get_recent_logs(limit=5)
    assert len(logs) == 5
    assert logs[0] == {"msg": "log 9"}

def test_memory_buffer_processor():
    from config.logging import LOG_BUFFER, memory_buffer_processor
    LOG_BUFFER.clear()
    
    event_dict = {"event": "test_event", "level": "info"}
    
    # Simulate structlog processor call
    result = memory_buffer_processor(None, "info", event_dict)
    
    assert result == event_dict
    assert len(LOG_BUFFER) == 1
    assert LOG_BUFFER[0] == event_dict
