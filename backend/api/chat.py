from fastapi import APIRouter, UploadFile, File, Form
from pydantic import BaseModel
from agents.orchestrator import create_orchestrator_graph
from langchain_core.messages import HumanMessage
import os
import shutil
from typing import Optional

router = APIRouter()

orchestrator_graph = create_orchestrator_graph()

# Store conversation states in memory (use Redis/DB in production)
conversation_states = {}


class ChatRequest(BaseModel):
    message: str
    session_id: Optional[str] = "default"


class ChatResponse(BaseModel):
    response: str
    conversation_step: str
    journey_name: Optional[str] = None
    document_type: Optional[str] = None


@router.post("/chat", response_model=ChatResponse)
async def chat(request: ChatRequest):
    """Chat endpoint for orchestrator agent"""
    
    session_id = request.session_id
    
    # Get or create session state
    if session_id not in conversation_states:
        conversation_states[session_id] = {
            "messages": [],
            "user_input": "",
            "selected_option": None,
            "journey_name": None,
            "conversation_step": "initial",
            "document_type": None
        }
    
    state = conversation_states[session_id]
    state["user_input"] = request.message
    state["messages"].append(HumanMessage(content=request.message))
    
    result = orchestrator_graph.invoke(state)
    
    # Update session state
    conversation_states[session_id] = result
    
    ai_messages = [msg for msg in result["messages"] if hasattr(msg, "content")]
    response_text = ai_messages[-1].content if ai_messages else "Error processing request"
    
    # Clean up markdown formatting (remove ** for bold)
    response_text = response_text.replace("**", "")
    
    return ChatResponse(
        response=response_text,
        conversation_step=result.get("conversation_step", "initial"),
        journey_name=result.get("journey_name"),
        document_type=result.get("document_type")
    )


@router.post("/upload")
async def upload_document(
    file: UploadFile = File(...),
    journey_name: str = Form(...),
    document_type: str = Form(None),
    session_id: str = Form("default")
):
    """Upload PDF document to journey folder"""
    
    # Validate PDF
    if not file.filename.endswith('.pdf'):
        return {"error": "Only PDF files are allowed"}
    
    # Create directory structure
    if document_type:
        # For existing journey with document type
        upload_path = f"documents/journeys/{journey_name}/{document_type}"
    else:
        # For new journey
        upload_path = f"documents/journeys/{journey_name}"
    
    os.makedirs(upload_path, exist_ok=True)
    
    # Save file
    file_path = os.path.join(upload_path, file.filename)
    with open(file_path, "wb") as buffer:
        shutil.copyfileobj(file.file, buffer)
    
    # Update conversation state to notify about test case generation
    if session_id in conversation_states:
        from langchain_core.messages import AIMessage
        
        success_message = f"Document '{file.filename}' has been uploaded successfully! 🎉\n\nTest cases are now being generated for your journey. This may take a few moments..."
        
        conversation_states[session_id] = {
            "messages": [AIMessage(content=success_message)],
            "user_input": "",
            "selected_option": None,
            "journey_name": journey_name,
            "conversation_step": "document_uploaded",
            "document_type": document_type
        }
    
    return {
        "message": "Document uploaded successfully. Test cases are being generated.",
        "path": file_path,
        "filename": file.filename,
        "journey_name": journey_name
    }
