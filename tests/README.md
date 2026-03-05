# Test Suite for AI Chatbot

This directory contains comprehensive tests for the document processing functionality.

## Running Tests

```bash
# Install test dependencies
pip install pytest pytest-mock pytest-cov

# Run all tests
python3 -m pytest tests/ -v

# Run with coverage
python3 -m pytest tests/ --cov=app2 --cov-report=html

# Run specific test file
python3 -m pytest tests/test_document_processing.py -v

# Run specific test class
python3 -m pytest tests/test_document_processing.py::TestFileValidation -v
```

## Test Structure

- `test_document_processing.py` - Unit tests for file validation, extraction, PNG OCR
- `test_api_endpoints.py` - Integration tests for API endpoints
- `fixtures/` - Sample test files (PDF, CSV, PNG, etc.)

## Test Coverage

- **File Validation**: Tests that only PDF, CSV, PNG are accepted
- **File Extraction**: Tests that all formats extract text correctly
- **PNG OCR**: Tests DeepInfra API integration with mocks
- **API Endpoints**: Tests /api/ingest and /api/ingest-folder endpoints
- **Dependencies**: Verifies removed packages are not importable

## Notes

- PNG tests use mocked DeepInfra API calls (no real API key needed for unit tests)
- API endpoint tests require ChromaDB and Flask services running
- Dependency tests will pass after running `pip install -r requirements.txt` in a fresh environment
