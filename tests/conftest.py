"""
Pytest configuration file for the ez-clip test suite.
"""

import os
import sys
import pytest

# Add the parent directory to sys.path to allow imports from the root directory
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

# Define custom markers for categorizing tests
def pytest_configure(config):
    """Configure custom pytest markers."""
    config.addinivalue_line("markers", "optional: mark test as optional (may be skipped)")
    config.addinivalue_line("markers", "integration: mark test as an integration test")
    config.addinivalue_line("markers", "slow: mark test as slow (may take longer to run)")

# Setup logging for tests
@pytest.fixture(scope="session", autouse=True)
def setup_logging():
    """Configure logging for tests."""
    import logging
    logging.basicConfig(
        level=logging.INFO,
        format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
    )
    yield
    # Teardown (if needed) 