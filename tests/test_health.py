"""
E2E tests for health check and basic API endpoints
"""
import pytest
import httpx


@pytest.mark.e2e
class TestHealthEndpoints:
    """Test basic health and root endpoints"""

    @pytest.mark.asyncio
    async def test_root_endpoint(self, client: httpx.AsyncClient):
        """Test root endpoint returns welcome message"""
        response = await client.get("/")
        assert response.status_code == 200
        data = response.json()
        assert "message" in data
        assert "TraceQA" in data["message"]

    @pytest.mark.asyncio
    async def test_health_check(self, client: httpx.AsyncClient):
        """Test health check endpoint"""
        response = await client.get("/health")
        assert response.status_code == 200
        data = response.json()
        assert data["status"] == "healthy"

    @pytest.mark.asyncio
    async def test_backend_accessible(self, client: httpx.AsyncClient):
        """Test that backend is accessible and responding"""
        response = await client.get("/health")
        assert response.status_code == 200
