# Contributing Guide

Thank you for your interest in contributing to EasyVid! This document provides guidelines and instructions for contributing to the project.

## Table of Contents

- [Code of Conduct](#code-of-conduct)
- [Getting Started](#getting-started)
- [Development Setup](#development-setup)
- [Making Changes](#making-changes)
- [Submitting a Pull Request](#submitting-a-pull-request)
- [Coding Standards](#coding-standards)
- [Testing](#testing)
- [Documentation](#documentation)
- [Issue Reporting](#issue-reporting)
- [Feature Requests](#feature-requests)

## Code of Conduct

Please read and follow our [Code of Conduct](CODE_OF_CONDUCT.md) to foster an inclusive and respectful community.

## Getting Started

1. **Fork the repository** on GitHub
2. **Clone your fork** to your local development environment
3. **Set up the development environment** (see below)
4. **Create a new branch** for your contribution
5. **Make your changes** following the coding standards
6. **Write tests** to validate your changes
7. **Submit a pull request** to the original repository

## Development Setup

1. Ensure you have all prerequisites installed:
   - Python 3.9+
   - FFmpeg
   - Git

2. Clone your fork of the repository:
   ```bash
   git clone https://github.com/yourusername/easy-vid.git
   cd easy-vid
   ```

3. Create and activate a virtual environment:
   ```bash
   python -m venv venv
   source venv/bin/activate  # On Windows: venv\Scripts\activate
   ```

4. Install development dependencies:
   ```bash
   pip install -r ez_clip_app/requirements.txt
   pip install -r dev-requirements.txt
   ```

5. Set up pre-commit hooks:
   ```bash
   pre-commit install
   ```

## Making Changes

1. Create a new branch for your changes:
   ```bash
   git checkout -b feature/your-feature-name
   ```

2. Make your changes following the [coding standards](#coding-standards)

3. Run the tests to ensure your changes don't break existing functionality:
   ```bash
   pytest
   ```

4. Run linting to ensure code quality:
   ```bash
   flake8
   ```

5. Commit your changes with a descriptive message:
   ```bash
   git commit -m "Add feature X that does Y"
   ```

## Submitting a Pull Request

1. Push your branch to your fork:
   ```bash
   git push origin feature/your-feature-name
   ```

2. Go to the original repository on GitHub and create a Pull Request

3. Include in your PR description:
   - A clear description of what your changes do
   - Any relevant issue numbers (e.g., "Closes #123")
   - Any special considerations or notes for reviewers

4. Wait for a maintainer to review your PR

5. Address any feedback or requested changes

## Coding Standards

We follow a consistent coding style across the project:

- Follow [PEP 8](https://www.python.org/dev/peps/pep-0008/) guidelines
- Use 4 spaces for indentation (no tabs)
- Maximum line length of 100 characters
- Use docstrings for all modules, classes, and functions
- Include type hints for function parameters and return values
- Use descriptive variable and function names
- Write comments for complex sections of code

## Testing

All new features and bug fixes should include tests:

- Unit tests for individual functions and classes
- Integration tests for components working together
- Tests should be placed in the `tests/` directory
- Use pytest for writing and running tests
- Ensure all tests pass before submitting a PR

Running tests:
```bash
# Run all tests
pytest

# Run tests with coverage report
pytest --cov=ez_clip_app

# Run specific test file
pytest tests/test_transcribe.py
```

## Documentation

Good documentation is essential:

- Update the relevant documentation files in the `docs/` directory
- Document all public functions, classes, and methods
- Provide examples for complex functionality
- Keep the README up to date
- Use markdown for documentation files

## Issue Reporting

If you find a bug or have a suggestion:

1. Check existing issues to see if it has already been reported
2. Create a new issue with a descriptive title and detailed information
3. Include steps to reproduce for bugs
4. Mention your environment details (OS, Python version, etc.)
5. Add relevant labels

## Feature Requests

For feature requests:

1. Explain the feature and its benefits
2. Provide examples of how it would be used
3. Consider implementation details and potential challenges
4. Discuss alternatives you've considered

---

Thank you for contributing to EasyVid! Your efforts help make this project better for everyone.