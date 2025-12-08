"""
Pytest configuration and fixtures for E2E tests
"""
import pytest
import httpx
import os
from pathlib import Path
import tempfile
import shutil
from typing import Generator
import time

# Backend URL - can be overridden with environment variable
BACKEND_URL = os.getenv("BACKEND_URL", "http://localhost:8000")
FRONTEND_URL = os.getenv("FRONTEND_URL", "http://localhost:3000")

# Test timeout settings
REQUEST_TIMEOUT = 30.0
LONG_TIMEOUT = 120.0  # For long-running operations like document processing


@pytest.fixture(scope="session")
def backend_url() -> str:
    """Backend API base URL"""
    return BACKEND_URL


@pytest.fixture(scope="session")
def frontend_url() -> str:
    """Frontend API base URL"""
    return FRONTEND_URL


@pytest.fixture(scope="function")
def client(backend_url: str) -> Generator[httpx.AsyncClient, None, None]:
    """HTTP client for making requests to backend"""
    with httpx.AsyncClient(base_url=backend_url, timeout=REQUEST_TIMEOUT) as client:
        yield client


@pytest.fixture(scope="function")
def frontend_client(frontend_url: str) -> Generator[httpx.AsyncClient, None, None]:
    """HTTP client for making requests to frontend (Next.js API routes)"""
    with httpx.AsyncClient(base_url=frontend_url, timeout=REQUEST_TIMEOUT, follow_redirects=True) as client:
        yield client


@pytest.fixture(scope="function")
def test_session_id() -> str:
    """Generate a unique session ID for each test"""
    return f"test_session_{int(time.time() * 1000)}"


@pytest.fixture(scope="function")
def test_journey_name() -> str:
    """Generate a unique journey name for each test"""
    return f"test_journey_{int(time.time() * 1000)}"


@pytest.fixture(scope="function")
def sample_pdf_content() -> bytes:
    """Generate a minimal valid PDF content for testing"""
    # Minimal PDF structure (valid PDF header and basic structure)
    pdf_content = b"""%PDF-1.4
1 0 obj
<<
/Type /Catalog
/Pages 2 0 R
>>
endobj
2 0 obj
<<
/Type /Pages
/Kids [3 0 R]
/Count 1
>>
endobj
3 0 obj
<<
/Type /Page
/Parent 2 0 R
/MediaBox [0 0 612 792]
/Contents 4 0 R
/Resources <<
/Font <<
/F1 <<
/Type /Font
/Subtype /Type1
/BaseFont /Helvetica
>>
>>
>>
>>
endobj
4 0 obj
<<
/Length 44
>>
stream
BT
/F1 12 Tf
100 700 Td
(Test Document) Tj
ET
endstream
endobj
xref
0 5
0000000000 65535 f 
0000000009 00000 n 
0000000058 00000 n 
0000000115 00000 n 
0000000314 00000 n 
trailer
<<
/Size 5
/Root 1 0 R
>>
startxref
398
%%EOF"""
    return pdf_content


@pytest.fixture(scope="function")
def temp_documents_dir(tmp_path: Path) -> Generator[Path, None, None]:
    """Create a temporary documents directory for testing"""
    docs_dir = tmp_path / "documents"
    docs_dir.mkdir(parents=True, exist_ok=True)
    yield docs_dir
    # Cleanup
    if docs_dir.exists():
        shutil.rmtree(docs_dir, ignore_errors=True)


def wait_for_condition(
    condition_func,
    timeout: float = 30.0,
    interval: float = 1.0,
    error_message: str = "Condition not met within timeout"
):
    """Wait for a condition to be true"""
    start_time = time.time()
    while time.time() - start_time < timeout:
        if condition_func():
            return True
        time.sleep(interval)
    raise TimeoutError(error_message)


@pytest.fixture(scope="function")
def wait_for_processing():
    """Helper fixture to wait for background processing to complete"""
    async def _wait(job_id: str, client: httpx.AsyncClient, timeout: float = LONG_TIMEOUT):
        """Wait for a processing job to complete"""
        import asyncio
        start_time = time.time()
        while time.time() - start_time < timeout:
            response = await client.get(f"/api/processing-status/{job_id}")
            if response.status_code == 200:
                status_data = response.json()
                if status_data.get("status") in ["completed", "failed"]:
                    return status_data
            await asyncio.sleep(2.0)
        raise TimeoutError(f"Processing job {job_id} did not complete within {timeout} seconds")
    return _wait
