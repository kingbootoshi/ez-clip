#!/usr/bin/env python3
"""
Test script to verify imports are working correctly.
"""

import sys
import os

# Add the parent directory to sys.path to allow imports from the root directory
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

try:
    print("Testing imports...")
    
    # Test config imports
    from ez_clip_app.config import DEFAULT_MODEL_SIZE, DEVICE
    print(f"Config imports OK. Default model: {DEFAULT_MODEL_SIZE}, Device: {DEVICE}")
    
    # Test database imports
    from ez_clip_app.data.database import DB
    print("Database imports OK")
    
    # Test core imports
    from ez_clip_app.core.pipeline import process_file, JobSettings
    print("Pipeline imports OK")
    
    # Test UI imports (this may fail if PySide6 is not installed)
    try:
        from ez_clip_app.ui.desktop_gui import MainWindow
        print("UI imports OK")
    except ImportError as e:
        print(f"UI imports failed: {e}")
    
    print("All imports tested successfully!")

except Exception as e:
    print(f"Import error: {e}") 