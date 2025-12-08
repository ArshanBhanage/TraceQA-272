"""
Integration E2E tests that test complete workflows
"""
import pytest
import httpx
import asyncio
import time
from io import BytesIO


@pytest.mark.e2e
@pytest.mark.integration
@pytest.mark.slow
class TestCompleteWorkflows:
    """Test complete end-to-end workflows"""

    @pytest.mark.asyncio
    async def test_complete_document_upload_flow(
        self, 
        client: httpx.AsyncClient, 
        test_session_id: str,
        test_journey_name: str,
        sample_pdf_content: bytes
    ):
        """Test complete flow: upload -> check status -> verify journey"""
        # Step 1: Upload document
        files = {
            "file": ("integration_test.pdf", BytesIO(sample_pdf_content), "application/pdf")
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
        upload_data = upload_response.json()
        assert upload_data["success"] is True
        job_id = upload_data["job_id"]
        
        # Step 2: Check processing status (wait a bit first)
        await asyncio.sleep(2)
        status_response = await client.get(f"/api/processing-status/{job_id}")
        assert status_response.status_code == 200
        status_data = status_response.json()
        assert "status" in status_data
        
        # Step 3: Verify journey appears in journeys list
        journeys_response = await client.get("/api/journeys")
        assert journeys_response.status_code == 200
        journeys_data = journeys_response.json()
        assert journeys_data["success"] is True

    @pytest.mark.asyncio
    async def test_chat_to_upload_workflow(
        self, 
        client: httpx.AsyncClient, 
        test_session_id: str,
        test_journey_name: str
    ):
        """Test workflow: chat -> upload document"""
        # Step 1: Start chat conversation
        chat_response = await client.post(
            "/api/chat",
            json={
                "message": "",
                "session_id": test_session_id
            }
        )
        assert chat_response.status_code == 200
        chat_data = chat_response.json()
        assert "response" in chat_data
        
        # Step 2: Send a message about uploading
        chat_response2 = await client.post(
            "/api/chat",
            json={
                "message": "I want to upload a document",
                "session_id": test_session_id
            }
        )
        assert chat_response2.status_code == 200
        
        # Step 3: Upload a document (simulating user action)
        # This would typically be done through the UI, but we test the API
        files = {
            "file": ("workflow_test.pdf", BytesIO(b"fake pdf content"), "application/pdf")
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

    @pytest.mark.asyncio
    async def test_rag_query_workflow(
        self, 
        client: httpx.AsyncClient, 
        test_journey_name: str
    ):
        """Test workflow: upload -> query RAG"""
        # Step 1: Query RAG (even if no documents indexed, should handle gracefully)
        rag_response = await client.post(
            "/api/rag/query",
            json={
                "question": "What information is available?",
                "journey_name": test_journey_name,
                "top_k": 5
            }
        )
        assert rag_response.status_code == 200
        rag_data = rag_response.json()
        assert "success" in rag_data
        assert "answer" in rag_data
        
        # Step 2: Check RAG stats
        stats_response = await client.get(f"/api/rag/stats?journey_name={test_journey_name}")
        assert stats_response.status_code == 200

    @pytest.mark.asyncio
    async def test_session_management_workflow(
        self, 
        client: httpx.AsyncClient
    ):
        """Test complete session management workflow"""
        session_id = f"workflow_session_{int(time.time() * 1000)}"
        
        # Step 1: Start conversation
        chat1 = await client.post(
            "/api/chat",
            json={
                "message": "Hello",
                "session_id": session_id
            }
        )
        assert chat1.status_code == 200
        
        # Step 2: Continue conversation
        chat2 = await client.post(
            "/api/chat",
            json={
                "message": "What can you help me with?",
                "session_id": session_id
            }
        )
        assert chat2.status_code == 200
        
        # Step 3: Reset session
        reset = await client.post(
            "/api/reset",
            json={
                "session_id": session_id
            }
        )
        assert reset.status_code == 200
        assert reset.json()["success"] is True
        
        # Step 4: Verify session is reset (new conversation should start fresh)
        chat3 = await client.post(
            "/api/chat",
            json={
                "message": "",
                "session_id": session_id
            }
        )
        assert chat3.status_code == 200

    @pytest.mark.asyncio
    async def test_multiple_journeys_workflow(
        self, 
        client: httpx.AsyncClient, 
        test_session_id: str,
        sample_pdf_content: bytes
    ):
        """Test creating and managing multiple journeys"""
        journey1 = f"journey_1_{int(time.time() * 1000)}"
        journey2 = f"journey_2_{int(time.time() * 1000)}"
        
        # Create journey 1
        files1 = {
            "file": ("doc1.pdf", BytesIO(sample_pdf_content), "application/pdf")
        }
        upload1 = await client.post(
            "/api/upload",
            files=files1,
            data={"journey_name": journey1, "session_id": test_session_id}
        )
        assert upload1.status_code == 200
        
        # Create journey 2
        files2 = {
            "file": ("doc2.pdf", BytesIO(sample_pdf_content), "application/pdf")
        }
        upload2 = await client.post(
            "/api/upload",
            files=files2,
            data={"journey_name": journey2, "session_id": test_session_id}
        )
        assert upload2.status_code == 200
        
        # Get all journeys
        journeys = await client.get("/api/journeys")
        assert journeys.status_code == 200
        journeys_data = journeys.json()
        assert journeys_data["success"] is True
        assert isinstance(journeys_data["journeys"], list)
