# EZ-Clip Testing Guide

This document provides a comprehensive overview of the testing infrastructure for the EZ-Clip application. 

## Testing Philosophy

The EZ-Clip test suite follows these core principles:

1. **Fast and Deterministic**: Most tests are designed to complete in milliseconds by avoiding heavy ML operations. 
2. **Fixture-Based**: Tests use pre-generated fixtures instead of re-running expensive ML models.
3. **Isolation**: Each test operates in an isolated environment (in-memory databases, temporary files).
4. **Comprehensive Coverage**: Tests focus on core functionality: formatting, database operations, and pipeline logic.
5. **Selective Integration Testing**: Heavy, end-to-end tests are separated with specific markers.

## Test Suite Structure

```
tests/
  fixtures/              # JSON fixture data for testing
    multi_speakers_fixture.json  # Pre-generated transcription data
  expected/              # For snapshot testing (future use)
  test_clips/            # Sample audio/video clips for integration tests
    multi_speakers.mp4   # Test clip with multiple speakers
  conftest.py            # Pytest configuration and fixtures
  test_formatting.py     # Tests for text formatting
  test_database.py       # Tests for database CRUD operations
  test_pipeline_unit.py  # Tests for pipeline with mocked components
  test_pipeline_integration.py  # Slow tests with real ML models
```

## Main Test Categories

### 1. Formatting Tests

`test_formatting.py` verifies that the segment-to-markdown conversion works correctly:

- **Roundtrip Test**: Ensures fixture data can be formatted to markdown and matches expected output
- **Edge Cases**: Tests specific formatting scenarios like speaker transitions and text merging

### 2. Database Tests

`test_database.py` tests the SQLite database operations:

- **CRUD Operations**: Tests creation, reading, updating and deletion
- **Cascading Deletes**: Verifies that deleting a media file properly cascades to related records
- **Transaction Integrity**: Ensures database remains in a consistent state

### 3. Pipeline Unit Tests

`test_pipeline_unit.py` tests the main transcription pipeline without invoking heavy ML operations:

- **Mocked ML Components**: Uses fixture data instead of real transcription/diarization
- **End-to-End Flow**: Tests the complete pipeline workflow
- **State Transitions**: Verifies proper status updates (queued → running → done)

### 4. Integration Tests

`test_pipeline_integration.py` performs real ML operations with actual models:

- **Real Pipeline Testing**: Runs the actual transcription and diarization models
- **Fixture Comparison**: Ensures output is consistent with expected fixture data
- **Marked as Slow/Integration**: Separate categorization to exclude from regular test runs

## Key Test Fixtures

### 1. `fixture_data`

Contains pre-generated, serialized output from the ML pipeline including:
- Transcript segments with timestamps and speaker information
- Expected markdown output
- Duration information

### 2. `test_db`

An in-memory SQLite database fixture that:
- Initializes a clean database for each test
- Configures proper SQLite settings (foreign keys, row factory)
- Ensures isolation between tests

### 3. `patch_heavy_functions`

Replaces expensive ML operations with mocked versions that:
- Return pre-generated data from fixtures
- Complete instantly rather than taking seconds/minutes
- Provide consistent, deterministic output

## Running Tests

### Standard Test Run (Fast Tests Only)

```bash
# Run all tests except integration/slow tests
python -m pytest -m "not integration and not slow"
```

### With Coverage

```bash
# Run fast tests with coverage reporting
python -m pytest -m "not integration and not slow" --cov=ez_clip_app
```

### Specific Test Files

```bash
# Run just the formatting tests
python -m pytest tests/test_formatting.py -v
```

### Integration Tests (Slow)

```bash
# Run the slow, integration tests (requires GPU for diarization)
python -m pytest -m "integration and slow"
```

### All Tests

```bash
# Run all tests (including integration tests)
python -m pytest
```

## Test Markers

The test suite uses these pytest markers:

- `integration`: Tests that interact with external systems or use real ML models
- `slow`: Tests that take more than a few seconds to complete
- `optional`: Tests that may be skipped under certain conditions

## CI Integration

The test suite is designed to work well with CI pipelines:

- Fast tests run on every commit/PR
- Integration tests can be scheduled to run nightly or on-demand
- Coverage reporting to track test quality

## Adding New Tests

When adding new features, the following test-driven approach is recommended:

1. Create a fixture with expected inputs/outputs
2. Write tests that validate the expected behavior
3. Implement the feature to pass the tests
4. Add edge cases and boundary tests

## Test Dependencies

The test suite requires these packages:

- `pytest`: Core testing framework
- `pytest-mock`: For mocking functions
- `deepdiff`: For comparing complex nested structures
- `pytest-sugar`: For improved test output formatting
- `pytest-cov`: For coverage reporting