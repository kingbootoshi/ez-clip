#!/usr/bin/env python3
"""
Test module to verify imports are working correctly.
Uses pytest for automated testing of imports from different modules.
"""

import sys
import os
import pytest

# Add the parent directory to sys.path to allow imports from the root directory
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

def test_config_imports():
    """Test that configuration imports work correctly."""
    from ez_clip_app.config import DEFAULT_MODEL_SIZE, DEVICE
    assert DEFAULT_MODEL_SIZE is not None, "DEFAULT_MODEL_SIZE should be defined"
    assert DEVICE is not None, "DEVICE should be defined"

def test_database_imports():
    """Test that database imports work correctly."""
    from ez_clip_app.data.database import DB
    assert DB is not None, "DB class should be defined"

def test_pipeline_imports():
    """Test that core pipeline imports work correctly."""
    from ez_clip_app.core.pipeline import process_file, JobSettings
    assert callable(process_file), "process_file should be a callable"
    assert JobSettings is not None, "JobSettings should be defined"

@pytest.mark.optional
def test_ui_imports():
    """
    Test that UI imports work correctly.
    This test is marked as optional since it requires PySide6.
    """
    try:
        from ez_clip_app.ui.main_window import MainWindow
        assert MainWindow is not None, "MainWindow should be defined"
    except ImportError as e:
        pytest.skip(f"UI imports failed (this is acceptable if PySide6 is not installed): {e}") 