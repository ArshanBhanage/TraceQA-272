from fastapi import APIRouter, UploadFile, File, Form
from pydantic import BaseModel
from agents.orchestrator import create_orchestrator_graph
from agents.landing_ai_agent import create_landing_ai_agent
from agents.test_case_generator_agent import create_test_case_generator_agent
from langchain_core.messages import HumanMessage, AIMessage
from config import DOCUMENTS_DIR
import os
import shutil
from typing import Optional

router = APIRouter()

orchestrator_graph = create_orchestrator_graph()
landing_ai_agent = create_landing_ai_agent()
test_case_generator = create_test_case_generator_agent()

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
    
    # Handle empty message (used for getting initial/next message without user input)
    if not request.message.strip():
        # If conversation just started or needs reset, invoke initial flow
        if state["conversation_step"] == "initial":
            state["user_input"] = ""
        elif state["conversation_step"] == "document_uploaded":
            # Document was just uploaded, continue to next step
            state["user_input"] = ""
        else:
            # Empty message at other steps, just return current state
            ai_messages = [msg for msg in state["messages"] if hasattr(msg, "content")]
            response_text = ai_messages[-1].content if ai_messages else "How can I help you?"
            return ChatResponse(
                response=response_text,
                conversation_step=state.get("conversation_step", "initial"),
                journey_name=state.get("journey_name"),
                document_type=state.get("document_type")
            )
    else:
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
    
    # Create directory structure using centralized path config
    if document_type:
        # For existing journey with document type
        upload_path = DOCUMENTS_DIR / "journeys" / journey_name / document_type
    else:
        # For new journey
        upload_path = DOCUMENTS_DIR / "journeys" / journey_name
    
    upload_path.mkdir(parents=True, exist_ok=True)
    
    # Save file
    file_path = upload_path / file.filename
    with open(file_path, "wb") as buffer:
        shutil.copyfileobj(file.file, buffer)
    
    # Process document with Landing AI
    try:
        landing_ai_result = landing_ai_agent.process_document(
            document_path=str(file_path),
            journey_name=journey_name,
            document_type=document_type
        )
        
        parse_success = True
        chunks_count = len(landing_ai_result.get("chunks", []))
        
        # Generate test cases from chunks
        print(f"[INFO] Starting test case generation for {file.filename}")
        test_case_result = test_case_generator.process_document(
            journey_name=journey_name,
            document_filename=file.filename,
            parse_result=landing_ai_result.get("parse_result", {}),
            document_type=document_type
        )
        
        total_test_cases = test_case_result.get("summary", {}).get("total_test_cases", 0)
        print(f"[INFO] Generated {total_test_cases} test cases for {file.filename}")
        
        # Merge test cases for entire journey
        print(f"[INFO] Merging all test cases for journey: {journey_name}")
        merged_result = test_case_generator.merge_journey_test_cases(journey_name)
        total_merged_test_cases = merged_result.get("summary", {}).get("total_test_cases", 0)
        print(f"[INFO] Total test cases for journey '{journey_name}': {total_merged_test_cases}")
        
    except Exception as e:
        parse_success = False
        chunks_count = 0
        total_test_cases = 0
        total_merged_test_cases = 0
        print(f"Landing AI processing error: {str(e)}")
    
    # Update conversation state after upload
    if session_id in conversation_states:
        if parse_success:
            success_message = f"Document '{file.filename}' uploaded successfully!\n\nDocument parsed: {chunks_count} chunks extracted.\nGenerated {total_test_cases} test cases for this document.\nTotal test cases for journey '{journey_name}': {total_merged_test_cases}"
        else:
            success_message = f"Document '{file.filename}' uploaded successfully!"
        
        conversation_states[session_id] = {
            "messages": [AIMessage(content=success_message)],
            "user_input": "",
            "selected_option": None,
            "journey_name": journey_name,
            "conversation_step": "document_uploaded",
            "document_type": document_type
        }
    
    return {
        "message": "Document uploaded successfully. Test cases generated.",
        "path": file_path,
        "filename": file.filename,
        "journey_name": journey_name,
        "parse_success": parse_success,
        "chunks_count": chunks_count if parse_success else 0,
        "test_cases_generated": total_test_cases if parse_success else 0,
        "total_journey_test_cases": total_merged_test_cases if parse_success else 0
    }


@router.post("/reset")
async def reset_session(session_id: str = "default"):
    """Reset conversation session"""
    if session_id in conversation_states:
        del conversation_states[session_id]
    
    return {"message": "Session reset successfully"}
