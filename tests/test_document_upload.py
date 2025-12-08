"""
E2E tests for document upload and processing
"""
import pytest
import httpx
import time
from io import BytesIO


@pytest.mark.e2e
@pytest.mark.slow
class TestDocumentUpload:
    """Test document upload and processing endpoints"""

    @pytest.mark.asyncio
    async def test_upload_pdf_document(
        self, 
        client: httpx.AsyncClient, 
        test_session_id: str,
        test_journey_name: str,
        sample_pdf_content: bytes
    ):
        """Test uploading a PDF document"""
        # Create a file-like object
        files = {
            "file": ("test_document.pdf", BytesIO(sample_pdf_content), "application/pdf")
        }
        data = {
            "journey_name": test_journey_name,
            "session_id": test_session_id
        }
        
        response = await client.post(
            "/api/upload",
            files=files,
            data=data
        )
        
        assert response.status_code == 200
        response_data = response.json()
        assert response_data["success"] is True
        assert "job_id" in response_data
        assert "filename" in response_data
        assert response_data["filename"] == "test_document.pdf"
        assert response_data["journey_name"] == test_journey_name

    @pytest.mark.asyncio
    async def test_upload_non_pdf_rejected(
        self, 
        client: httpx.AsyncClient, 
        test_session_id: str,
        test_journey_name: str
    ):
        """Test that non-PDF files are rejected"""
        # Create a text file
        text_content = b"This is a text file, not a PDF"
        files = {
            "file": ("test.txt", BytesIO(text_content), "text/plain")
        }
        data = {
            "journey_name": test_journey_name,
            "session_id": test_session_id
        }
        
        response = await client.post(
            "/api/upload",
            files=files,
            data=data
        )
        
        # Should reject non-PDF files
        assert response.status_code == 200
        response_data = response.json()
        assert "error" in response_data
        assert "PDF" in response_data["error"]

    @pytest.mark.asyncio
    async def test_upload_with_document_type(
        self, 
        client: httpx.AsyncClient, 
        test_session_id: str,
        test_journey_name: str,
        sample_pdf_content: bytes
    ):
        """Test uploading a document with a document type"""
        files = {
            "file": ("test_document.pdf", BytesIO(sample_pdf_content), "application/pdf")
        }
        data = {
            "journey_name": test_journey_name,
            "document_type": "requirements",
            "session_id": test_session_id
        }
        
        response = await client.post(
            "/api/upload",
            files=files,
            data=data
        )
        
        assert response.status_code == 200
        response_data = response.json()
        assert response_data["success"] is True
        assert "job_id" in response_data

    @pytest.mark.asyncio
    async def test_processing_status_endpoint(
        self, 
        client: httpx.AsyncClient, 
        test_session_id: str,
        test_journey_name: str,
        sample_pdf_content: bytes
    ):
        """Test checking processing status"""
        # Upload a document first
        files = {
            "file": ("test_document.pdf", BytesIO(sample_pdf_content), "application/pdf")
        }
        data = {
            "journey_name": test_journey_name,
            "session_id": test_session_id
        }
        
        upload_response = await client.post(
            "/api/upload",
            files=files,
            data=data
        )
        assert upload_response.status_code == 200
        job_id = upload_response.json()["job_id"]
        
        # Check processing status
        status_response = await client.get(f"/api/processing-status/{job_id}")
        assert status_response.status_code == 200
        status_data = status_response.json()
        assert "status" in status_data
        assert "message" in status_data
        assert status_data["status"] in ["processing", "completed", "failed", "starting"]

    @pytest.mark.asyncio
    async def test_processing_status_not_found(self, client: httpx.AsyncClient):
        """Test processing status for non-existent job"""
        response = await client.get("/api/processing-status/nonexistent_job_id")
        assert response.status_code == 200
        data = response.json()
        assert data["status"] == "not_found"

    @pytest.mark.asyncio
    async def test_upload_missing_required_fields(self, client: httpx.AsyncClient):
        """Test upload endpoint with missing required fields"""
        # Missing journey_name
        files = {
            "file": ("test.pdf", BytesIO(b"fake pdf"), "application/pdf")
        }
        
        response = await client.post(
            "/api/upload",
            files=files
        )
        
        # Should return error (422 or 400)
        assert response.status_code in [400, 422]
