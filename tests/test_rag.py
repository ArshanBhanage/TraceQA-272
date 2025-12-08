"""
E2E tests for RAG (Retrieval Augmented Generation) functionality
"""
import pytest
import httpx


@pytest.mark.e2e
class TestRAGEndpoints:
    """Test RAG query endpoints"""

    @pytest.mark.asyncio
    async def test_rag_query_basic(self, client: httpx.AsyncClient):
        """Test basic RAG query"""
        response = await client.post(
            "/api/rag/query",
            json={
                "question": "What is this document about?",
                "top_k": 5
            }
        )
        assert response.status_code == 200
        data = response.json()
        assert "success" in data
        assert "answer" in data
        assert "question" in data
        assert "evidence" in data
        assert "sources_count" in data
        assert isinstance(data["evidence"], list)
        assert isinstance(data["sources_count"], int)

    @pytest.mark.asyncio
    async def test_rag_query_with_journey(
        self, 
        client: httpx.AsyncClient, 
        test_journey_name: str
    ):
        """Test RAG query with specific journey"""
        response = await client.post(
            "/api/rag/query",
            json={
                "question": "What are the main features?",
                "journey_name": test_journey_name,
                "top_k": 3
            }
        )
        assert response.status_code == 200
        data = response.json()
        assert "success" in data
        assert "answer" in data
        assert "question" in data

    @pytest.mark.asyncio
    async def test_rag_query_custom_top_k(self, client: httpx.AsyncClient):
        """Test RAG query with custom top_k parameter"""
        response = await client.post(
            "/api/rag/query",
            json={
                "question": "Test question",
                "top_k": 10
            }
        )
        assert response.status_code == 200
        data = response.json()
        assert "success" in data
        assert len(data["evidence"]) <= 10  # Should not exceed top_k

    @pytest.mark.asyncio
    async def test_rag_query_empty_question(self, client: httpx.AsyncClient):
        """Test RAG query with empty question"""
        response = await client.post(
            "/api/rag/query",
            json={
                "question": "",
                "top_k": 5
            }
        )
        # Should handle empty question (might return error or empty answer)
        assert response.status_code in [200, 400, 422]

    @pytest.mark.asyncio
    async def test_rag_stats(self, client: httpx.AsyncClient):
        """Test RAG stats endpoint"""
        response = await client.get("/api/rag/stats")
        assert response.status_code == 200
        data = response.json()
        # Stats endpoint should return data (structure may vary)
        assert isinstance(data, dict)

    @pytest.mark.asyncio
    async def test_rag_stats_with_journey(
        self, 
        client: httpx.AsyncClient, 
        test_journey_name: str
    ):
        """Test RAG stats endpoint with journey filter"""
        response = await client.get(
            f"/api/rag/stats?journey_name={test_journey_name}"
        )
        assert response.status_code == 200
        data = response.json()
        assert isinstance(data, dict)

    @pytest.mark.asyncio
    async def test_rag_query_invalid_request(self, client: httpx.AsyncClient):
        """Test RAG query with invalid request"""
        # Missing required field
        response = await client.post(
            "/api/rag/query",
            json={}
        )
        # Should return validation error
        assert response.status_code == 422
