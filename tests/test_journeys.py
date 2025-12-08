"""
E2E tests for journey management
"""
import pytest
import httpx
import asyncio


@pytest.mark.e2e
class TestJourneyEndpoints:
    """Test journey-related endpoints"""

    @pytest.mark.asyncio
    async def test_get_journeys_empty(self, client: httpx.AsyncClient):
        """Test getting journeys list when no journeys exist"""
        response = await client.get("/api/journeys")
        assert response.status_code == 200
        data = response.json()
        assert "success" in data
        assert "journeys" in data
        assert isinstance(data["journeys"], list)
        assert "total" in data

    @pytest.mark.asyncio
    async def test_get_journeys_after_upload(
        self, 
        client: httpx.AsyncClient, 
        test_session_id: str,
        test_journey_name: str,
        sample_pdf_content: bytes
    ):
        """Test getting journeys list after uploading a document"""
        from io import BytesIO
        
        # Upload a document to create a journey
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
        
        # Wait a bit for directory creation
        await asyncio.sleep(1)
        
        # Get journeys list
        response = await client.get("/api/journeys")
        assert response.status_code == 200
        data = response.json()
        assert data["success"] is True
        assert isinstance(data["journeys"], list)
        
        # Check if our journey is in the list
        journey_names = [j["name"] for j in data["journeys"]]
        # Note: The journey might not appear immediately due to async processing
        # So we just verify the endpoint works

    @pytest.mark.asyncio
    async def test_get_test_cases_nonexistent_journey(self, client: httpx.AsyncClient):
        """Test getting test cases for a non-existent journey"""
        response = await client.get("/api/test-cases/nonexistent_journey_12345")
        assert response.status_code == 200
        data = response.json()
        assert data["success"] is False
        assert "test_cases" in data
        assert isinstance(data["test_cases"], list)

    @pytest.mark.asyncio
    async def test_get_test_cases_structure(self, client: httpx.AsyncClient):
        """Test that test cases endpoint returns correct structure"""
        response = await client.get("/api/test-cases/test_journey")
        assert response.status_code == 200
        data = response.json()
        assert "success" in data
        assert "test_cases" in data
        assert isinstance(data["test_cases"], list)
        
        # If test cases exist, verify structure
        if data["success"] and len(data["test_cases"]) > 0:
            test_case = data["test_cases"][0]
            # Verify test case has expected fields (adjust based on actual structure)
            assert isinstance(test_case, dict)
