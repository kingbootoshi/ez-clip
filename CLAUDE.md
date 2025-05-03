# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Build and Test Commands

- Install dependencies: `pip install -r ez_clip_app/requirements.txt`
- Run application: `python -m ez_clip_app.main`
- Verbose logging: `python -m ez_clip_app.main -v`
- Run all tests: `pytest`
- Run single test: `pytest tests/test_file.py::test_function_name`
- Run tests with coverage: `pytest --cov=ez_clip_app`
- Lint code: `flake8`

## Code Style Guidelines

- Follow PEP 8 standards with max line length of 100 characters
- Use 4 spaces for indentation (no tabs)
- Include docstrings for all modules, classes, and functions
- Use type hints for function parameters and return values
- Use descriptive variable and function names
- Document all public functions, classes, and methods
- Import organization: standard library, third-party libraries, local modules
- Error handling: use custom exceptions and comprehensive error messages
- Use context managers (`with` statements) for resource management
- Class-based status enums for constants (see `config.py`)
- Follow SQLite database patterns in `database.py`
- Use pathlib for path handling rather than string concatenation
- Ensure proper error handling and file cleanup in try/except/finally blocks