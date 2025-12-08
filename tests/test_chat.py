"""
E2E tests for chat/orchestrator functionality
"""
import pytest
import httpx


@pytest.mark.e2e
class TestChatEndpoints:
    """Test chat and orchestrator endpoints"""

    @pytest.mark.asyncio
    async def test_chat_initial_message(self, client: httpx.AsyncClient, test_session_id: str):
        """Test initial chat message without user input"""
        response = await client.post(
            "/api/chat",
            json={
                "message": "",
                "session_id": test_session_id
            }
        )
        assert response.status_code == 200
        data = response.json()
        assert "response" in data
        assert "conversation_step" in data
        assert isinstance(data["response"], str)
        assert len(data["response"]) > 0

    @pytest.mark.asyncio
    async def test_chat_with_message(self, client: httpx.AsyncClient, test_session_id: str):
        """Test chat with a user message"""
        response = await client.post(
            "/api/chat",
            json={
                "message": "Hello, I want to create a new journey",
                "session_id": test_session_id
            }
        )
        assert response.status_code == 200
        data = response.json()
        assert "response" in data
        assert "conversation_step" in data
        assert isinstance(data["response"], str)

    @pytest.mark.asyncio
    async def test_chat_session_persistence(self, client: httpx.AsyncClient, test_session_id: str):
        """Test that chat session persists across multiple messages"""
        # First message
        response1 = await client.post(
            "/api/chat",
            json={
                "message": "I want to upload a document",
                "session_id": test_session_id
            }
        )
        assert response1.status_code == 200
        data1 = response1.json()
        
        # Second message in same session
        response2 = await client.post(
            "/api/chat",
            json={
                "message": "What should I do next?",
                "session_id": test_session_id
            }
        )
        assert response2.status_code == 200
        data2 = response2.json()
        
        # Both should have valid responses
        assert "response" in data1
        assert "response" in data2
        assert len(data1["response"]) > 0
        assert len(data2["response"]) > 0

    @pytest.mark.asyncio
    async def test_chat_different_sessions(self, client: httpx.AsyncClient):
        """Test that different sessions are isolated"""
        session1 = f"session_{1}"
        session2 = f"session_{2}"
        
        # Send message to session 1
        response1 = await client.post(
            "/api/chat",
            json={
                "message": "Session 1 message",
                "session_id": session1
            }
        )
        assert response1.status_code == 200
        
        # Send message to session 2
        response2 = await client.post(
            "/api/chat",
            json={
                "message": "Session 2 message",
                "session_id": session2
            }
        )
        assert response2.status_code == 200
        
        # Both should work independently
        assert "response" in response1.json()
        assert "response" in response2.json()

    @pytest.mark.asyncio
    async def test_reset_session(self, client: httpx.AsyncClient, test_session_id: str):
        """Test resetting a chat session"""
        # Create some conversation state
        await client.post(
            "/api/chat",
            json={
                "message": "Test message",
                "session_id": test_session_id
            }
        )
        
        # Reset the session
        response = await client.post(
            "/api/reset",
            json={
                "session_id": test_session_id
            }
        )
        assert response.status_code == 200
        data = response.json()
        assert data["success"] is True
        assert "reset" in data["message"].lower() or "success" in data["message"].lower()

    @pytest.mark.asyncio
    async def test_chat_invalid_request(self, client: httpx.AsyncClient):
        """Test chat endpoint with invalid request"""
        # Missing required field
        response = await client.post(
            "/api/chat",
            json={}
        )
        # Should return validation error (422)
        assert response.status_code == 422
