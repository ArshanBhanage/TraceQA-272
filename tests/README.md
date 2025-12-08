# TraceQA End-to-End Tests

This directory contains comprehensive end-to-end (E2E) tests for the TraceQA application.

## Test Structure

The test suite is organized into the following test files:

- **test_health.py** - Basic health check and root endpoint tests
- **test_chat.py** - Chat/orchestrator functionality tests
- **test_document_upload.py** - Document upload and processing tests
- **test_journeys.py** - Journey management tests
- **test_rag.py** - RAG (Retrieval Augmented Generation) query tests
- **test_test_cases.py** - Test case generation tests
- **test_integration.py** - Complete workflow integration tests

## Prerequisites

1. **Backend Server**: The FastAPI backend must be running
   ```bash
   cd backend
   uvicorn main:app --reload
   ```

2. **Frontend Server** (optional): For full E2E tests including frontend proxy, the Next.js frontend should be running
   ```bash
   cd frontend
   npm run dev
   ```

3. **Dependencies**: Install test dependencies
   ```bash
   cd backend
   pip install -r requirements.txt
   ```

## Running Tests

### Run All Tests

```bash
cd backend
pytest tests/
```

### Run Specific Test File

```bash
pytest tests/test_health.py
```

### Run Specific Test

```bash
pytest tests/test_health.py::TestHealthEndpoints::test_health_check
```

### Run Tests with Markers

```bash
# Run only E2E tests
pytest -m e2e

# Run only integration tests
pytest -m integration

# Run only slow tests
pytest -m slow

# Skip slow tests
pytest -m "not slow"
```

### Run Tests with Verbose Output

```bash
pytest -v tests/
```

### Run Tests with Coverage

```bash
pytest --cov=api --cov-report=html tests/
```

## Configuration

### Environment Variables

You can configure test behavior using environment variables:

- `BACKEND_URL` - Backend API URL (default: `http://localhost:8000`)
- `FRONTEND_URL` - Frontend API URL (default: `http://localhost:3000`)

Example:
```bash
BACKEND_URL=http://localhost:8000 pytest tests/
```

### Test Configuration

Test configuration is in `pytest.ini`. Key settings:

- **Markers**: Tests are marked with `@pytest.mark.e2e`, `@pytest.mark.integration`, `@pytest.mark.slow`
- **Timeouts**: Default request timeout is 30 seconds, long operations use 120 seconds
- **Async Mode**: Tests use `asyncio_mode = auto` for async test support

## Test Fixtures

The `conftest.py` file provides several useful fixtures:

- `client` - HTTP client for backend API requests
- `frontend_client` - HTTP client for frontend API requests
- `test_session_id` - Unique session ID for each test
- `test_journey_name` - Unique journey name for each test
- `sample_pdf_content` - Minimal valid PDF content for testing
- `wait_for_processing` - Helper to wait for background jobs to complete

## Writing New Tests

### Basic Test Structure

```python
import pytest
import httpx

@pytest.mark.e2e
class TestMyFeature:
    @pytest.mark.asyncio
    async def test_my_endpoint(self, client: httpx.AsyncClient):
        response = await client.get("/api/my-endpoint")
        assert response.status_code == 200
        data = response.json()
        assert "expected_field" in data
```

### Test Markers

Use appropriate markers for your tests:

- `@pytest.mark.e2e` - End-to-end tests
- `@pytest.mark.integration` - Integration tests
- `@pytest.mark.slow` - Tests that take a long time
- `@pytest.mark.requires_api_keys` - Tests requiring API keys

### Best Practices

1. **Isolation**: Each test should be independent and not rely on other tests
2. **Cleanup**: Use fixtures for cleanup (e.g., `temp_documents_dir`)
3. **Timeouts**: Use appropriate timeouts for long-running operations
4. **Assertions**: Make assertions specific and meaningful
5. **Error Handling**: Test both success and error cases

## Troubleshooting

### Tests Failing with Connection Errors

- Ensure the backend server is running on the expected port
- Check that `BACKEND_URL` environment variable is set correctly
- Verify no firewall is blocking the connection

### Tests Timing Out

- Some tests are marked as `@pytest.mark.slow` and may take longer
- Increase timeout values in `conftest.py` if needed
- Check that background processing jobs are completing

### Tests Failing Due to Missing Data

- Some tests may require documents to be uploaded first
- Check that test fixtures are creating necessary test data
- Verify that cleanup is not interfering with test execution

## CI/CD Integration

These tests can be integrated into CI/CD pipelines. Example GitHub Actions workflow:

```yaml
name: E2E Tests

on: [push, pull_request]

jobs:
  test:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v2
      - name: Set up Python
        uses: actions/setup-python@v2
        with:
          python-version: '3.9'
      - name: Install dependencies
        run: |
          cd backend
          pip install -r requirements.txt
      - name: Start backend
        run: |
          cd backend
          uvicorn main:app --host 0.0.0.0 --port 8000 &
      - name: Run tests
        run: |
          cd backend
          pytest tests/ -v
```

## Notes

- Tests use real HTTP requests to the backend API
- Some tests create actual files and directories (cleaned up automatically)
- Tests marked as `slow` may take several minutes to complete
- Tests are designed to be idempotent and can be run multiple times
