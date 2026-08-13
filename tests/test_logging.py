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
