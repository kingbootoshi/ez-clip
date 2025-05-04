# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Build and Test Commands

- Install dependencies: `pip install -r ez_clip_app/requirements.txt`
- Install dev dependencies: `pip install -r requirements-dev.txt`
- Run application: `python -m ez_clip_app.main`
- Verbose logging: `python -m ez_clip_app.main -v`
- Run fast tests only: `pytest -m "not integration and not slow"`
- Run specific test file: `pytest tests/test_formatting.py -v`
- Run specific test: `pytest tests/test_file.py::test_function_name`
- Run with coverage: `pytest -m "not integration and not slow" --cov=ez_clip_app`
- Run integration tests (slow): `pytest -m "integration and slow"`
- Lint code: `flake8`
- Format code: `black .`
- Sort imports: `isort .`

## Code Style Guidelines

- Follow PEP 8 standards with max line length of 100 characters
- Use 4 spaces for indentation (no tabs)
- Include docstrings for all modules, classes, and functions (Google style)
- Use type hints for function parameters and return values
- Import organization: standard library, third-party libraries, local modules
- Use pytest fixtures for test dependency injection
- Use mocks for expensive ML operations in unit tests
- Use pathlib for path handling rather than string concatenation
- Error handling: use custom exceptions and comprehensive error messages
- Use context managers (`with` statements) for resource management
- Class-based status enums for constants (see `config.py`)
- Follow SQLite database patterns in `database.py`
- Ensure proper error handling and file cleanup in try/except/finally blocks
- Test-driven development: write tests before implementing features