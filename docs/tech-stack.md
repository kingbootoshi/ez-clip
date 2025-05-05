# Tech Stack

This document outlines the primary technologies and libraries used in the EZ-Clip project.

## Core Speech Processing

*   **WhisperX:** Utilized for accurate and efficient speech-to-text transcription. Based on OpenAI's Whisper model, WhisperX provides word-level timestamps and speaker diarization capabilities.
    *   [WhisperX GitHub Repository](https://github.com/m-bain/whisperX)
*   **PyTorch:** Serves as the fundamental machine learning framework for running WhisperX and potentially other AI/ML models within the application.
    *   [PyTorch Website](https://pytorch.org/)
*   **pyannote.audio:** Employed for speaker diarization, identifying different speakers within an audio file.
    *   [pyannote.audio GitHub Repository](https://github.com/pyannote/pyannote-audio)
*   **ffmpeg-python:** Python bindings for FFmpeg, used for handling audio and video file processing, conversions, and manipulation required for the speech processing pipeline.
    *   [ffmpeg-python GitHub Repository](https://github.com/kkroening/ffmpeg-python)

## Application Framework & User Interface

*   **PySide6:** The official Python bindings for the Qt framework (version 6). Used for building the cross-platform graphical user interface (GUI) of the EZ-Clip application.
    *   [PySide6 Documentation](https://doc.qt.io/qtforpython/)

## Database

*   **SQLite:** The default relational database management system used for storing application data, such as project information, transcription results, and user settings. Managed via `sqlite-utils`.
    *   [SQLite Website](https://www.sqlite.org/index.html)
*   **sqlite-utils:** A Python library providing convenient utilities for interacting with SQLite databases.
    *   [sqlite-utils Documentation](https://sqlite-utils.datasette.io/en/stable/)

## Utility Libraries

*   **python-dotenv:** Loads environment variables from a `.env` file, useful for managing configuration settings (e.g., API keys, database paths) separately from the codebase.
    *   [python-dotenv PyPI](https://pypi.org/project/python-dotenv/)
*   **tqdm:** Provides progress bars for long-running operations, enhancing the user experience during tasks like file processing or transcription.
    *   [tqdm GitHub Repository](https://github.com/tqdm/tqdm)
*   **python-slugify:** Generates URL-friendly "slugs" from strings, potentially used for creating unique identifiers or filenames.
    *   [python-slugify GitHub Repository](https://github.com/un33k/python-slugify)

## Optional Dependencies

*   **matplotlib:** A comprehensive library for creating static, animated, and interactive visualizations in Python. Potentially used for displaying audio waveforms or other data visualizations.
    *   [matplotlib Website](https://matplotlib.org/)
*   **Pydantic:** Data validation and settings management using Python type annotations. Likely used for ensuring data integrity and managing application configuration.
    *   [Pydantic Documentation](https://docs.pydantic.dev/) 