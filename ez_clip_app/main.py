#!/usr/bin/env python3
"""
Main entry point for the EZ Clip transcription app.
"""
import sys
import logging
import argparse
from pathlib import Path

from PySide6.QtWidgets import QApplication
from ez_clip_app.ui.desktop_gui import MainWindow

# Configure logging
def setup_logging(verbose=False):
    """Set up logging configuration."""
    log_level = logging.DEBUG if verbose else logging.INFO
    log_format = '%(asctime)s - %(name)s - %(levelname)s - %(message)s'
    
    # Configure root logger
    logging.basicConfig(
        level=log_level,
        format=log_format,
        handlers=[
            logging.StreamHandler(),
            logging.FileHandler(Path.home() / '.ez_clip_app.log')
        ]
    )
    
    # Set more restrictive log level for noisy libraries
    logging.getLogger('matplotlib').setLevel(logging.WARNING)
    logging.getLogger('PIL').setLevel(logging.WARNING)
    logging.getLogger('pytorch_lightning').setLevel(logging.WARNING)

def main():
    """Main entry point."""
    parser = argparse.ArgumentParser(description='WhisperX transcription application')
    parser.add_argument('-v', '--verbose', action='store_true', help='Enable verbose logging')
    
    args = parser.parse_args()
    setup_logging(args.verbose)
    
    logger = logging.getLogger(__name__)
    logger.info("Starting WhisperXtranscription application")
    
    app = QApplication(sys.argv)
    window = MainWindow()
    window.show()
    sys.exit(app.exec())

if __name__ == '__main__':
    main()