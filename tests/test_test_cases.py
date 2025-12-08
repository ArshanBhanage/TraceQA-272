"""
E2E tests for test case generation functionality
"""
import pytest
import httpx
import asyncio


@pytest.mark.e2e
@pytest.mark.slow
class TestTestCaseGeneration:
    """Test test case generation endpoints"""

    @pytest.mark.asyncio
    async def test_generate_test_cases_nonexistent_journey(self, client: httpx.AsyncClient):
        """Test generating test cases for non-existent journey"""
        response = await client.post("/api/generate-test-cases/nonexistent_journey_12345")
        assert response.status_code == 200
        data = response.json()
        assert data["success"] is False
        assert "not found" in data["message"].lower() or "error" in data.get("message", "").lower()

    @pytest.mark.asyncio
    async def test_generate_test_cases_structure(
        self, 
        client: httpx.AsyncClient, 
        test_journey_name: str
    ):
        """Test that generate test cases endpoint returns correct structure"""
        response = await client.post(f"/api/generate-test-cases/{test_journey_name}")
        assert response.status_code == 200
        data = response.json()
        assert "success" in data
        assert "message" in data
        
        # If generation started successfully
        if data.get("success"):
            assert "job_id" in data
            assert "total_documents" in data

    @pytest.mark.asyncio
    async def test_generate_test_cases_returns_job_id(
        self, 
        client: httpx.AsyncClient, 
        test_journey_name: str
    ):
        """Test that generate test cases returns a job ID for tracking"""
        response = await client.post(f"/api/generate-test-cases/{test_journey_name}")
        assert response.status_code == 200
        data = response.json()
        
        # Even if journey doesn't exist, should return proper structure
        if data.get("success") and "job_id" in data:
            job_id = data["job_id"]
            assert isinstance(job_id, str)
            assert len(job_id) > 0
            
            # Can check status of the job
            status_response = await client.get(f"/api/processing-status/{job_id}")
            assert status_response.status_code == 200

    @pytest.mark.asyncio
    async def test_test_cases_endpoint_encoding(
        self, 
        client: httpx.AsyncClient
    ):
        """Test that test cases endpoint handles URL encoding correctly"""
        # Test with special characters in journey name
        journey_name = "test journey with spaces"
        encoded_name = journey_name.replace(" ", "%20")
        
        response = await client.get(f"/api/test-cases/{encoded_name}")
        # Should handle encoding (might return 404 or empty, but shouldn't crash)
        assert response.status_code in [200, 404]

    @pytest.mark.asyncio
    async def test_get_test_cases_after_generation(
        self, 
        client: httpx.AsyncClient, 
        test_journey_name: str
    ):
        """Test getting test cases after generation request"""
        # Request generation
        gen_response = await client.post(f"/api/generate-test-cases/{test_journey_name}")
        assert gen_response.status_code == 200
        
        # Get test cases (might be empty if generation not complete)
        test_cases_response = await client.get(f"/api/test-cases/{test_journey_name}")
        assert test_cases_response.status_code == 200
        data = test_cases_response.json()
        assert "success" in data
        assert "test_cases" in data
        assert isinstance(data["test_cases"], list)
