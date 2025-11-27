from fastapi import APIRouter, UploadFile, File, Form
from pydantic import BaseModel
from agents.orchestrator import create_orchestrator_graph
from agents.landing_ai_agent import create_landing_ai_agent
from agents.test_case_generator_agent import create_test_case_generator_agent
from langchain_core.messages import HumanMessage, AIMessage
from config import DOCUMENTS_DIR
import os
import shutil
import asyncio
import json
from typing import Optional

router = APIRouter()

orchestrator_graph = create_orchestrator_graph()
landing_ai_agent = create_landing_ai_agent()
test_case_generator = create_test_case_generator_agent()

# Store conversation states in memory (use Redis/DB in production)
conversation_states = {}

# Store processing status for background jobs
processing_status = {}


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


def process_document_background(
    file_path: str,
    filename: str,
    journey_name: str,
    document_type: Optional[str],
    session_id: str
):
    """Background task to process document with Landing AI and generate test cases"""
    job_id = f"{session_id}_{filename}"
    
    try:
        processing_status[job_id] = {
            "status": "processing",
            "stage": "parsing",
            "message": "Parsing document with Landing AI..."
        }
        
        # Process document with Landing AI
        landing_ai_result = landing_ai_agent.process_document(
            document_path=file_path,
            journey_name=journey_name,
            document_type=document_type
        )
        
        chunks_count = len(landing_ai_result.get("chunks", []))
        
        processing_status[job_id] = {
            "status": "processing",
            "stage": "generating_tests",
            "message": f"Parsed {chunks_count} chunks. Generating test cases..."
        }
        
        # Generate test cases from chunks
        print(f"[INFO] Starting test case generation for {filename}")
        test_case_result = test_case_generator.process_document(
            journey_name=journey_name,
            document_filename=filename,
            parse_result=landing_ai_result.get("parse_result", {}),
            document_type=document_type
        )
        
        total_test_cases = test_case_result.get("summary", {}).get("total_test_cases", 0)
        print(f"[INFO] Generated {total_test_cases} test cases for {filename}")
        
        processing_status[job_id] = {
            "status": "processing",
            "stage": "merging",
            "message": f"Generated {total_test_cases} test cases. Merging journey results..."
        }
        
        # Merge test cases for entire journey
        print(f"[INFO] Merging all test cases for journey: {journey_name}")
        merged_result = test_case_generator.merge_journey_test_cases(journey_name)
        total_merged_test_cases = merged_result.get("summary", {}).get("total_test_cases", 0)
        print(f"[INFO] Total test cases for journey '{journey_name}': {total_merged_test_cases}")
        
        # Update status to completed
        processing_status[job_id] = {
            "status": "completed",
            "stage": "done",
            "message": f"✅ Processing complete!\n\n📄 Document: {filename}\n📊 Chunks extracted: {chunks_count}\n🧪 Test cases generated: {total_test_cases}\n📋 Total journey test cases: {total_merged_test_cases}",
            "chunks_count": chunks_count,
            "test_cases": total_test_cases,
            "total_journey_test_cases": total_merged_test_cases
        }
        
        # Update conversation state
        if session_id in conversation_states:
            conversation_states[session_id] = {
                "messages": [AIMessage(content=processing_status[job_id]["message"])],
                "user_input": "",
                "selected_option": None,
                "journey_name": journey_name,
                "conversation_step": "document_uploaded",
                "document_type": document_type
            }
        
    except Exception as e:
        error_msg = f"❌ Error processing document: {str(e)}"
        print(f"[ERROR] Background processing failed: {str(e)}")
        processing_status[job_id] = {
            "status": "failed",
            "stage": "error",
            "message": error_msg,
            "error": str(e)
        }
        
        # Update conversation state with error
        if session_id in conversation_states:
            conversation_states[session_id] = {
                "messages": [AIMessage(content=error_msg)],
                "user_input": "",
                "selected_option": None,
                "journey_name": journey_name,
                "conversation_step": "document_uploaded",
                "document_type": document_type
            }


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
    
    # Create job_id and initialize status
    job_id = f"{session_id}_{file.filename}"
    processing_status[job_id] = {
        "status": "processing",
        "stage": "starting",
        "message": "Starting document processing..."
    }
    
    # Fire and forget - true background execution using asyncio
    asyncio.create_task(
        asyncio.to_thread(
            process_document_background,
            str(file_path),
            file.filename,
            journey_name,
            document_type,
            session_id
        )
    )
    
    # Return immediate response
    return {
        "success": True,
        "message": "✅ Got your file. I'm processing it now — this can take a few minutes. I'll send the results as soon as they're ready.",
        "filename": file.filename,
        "journey_name": journey_name,
        "job_id": job_id
    }


@router.get("/processing-status/{job_id}")
async def get_processing_status(job_id: str):
    """Get status of background document processing"""
    if job_id in processing_status:
        return processing_status[job_id]
    return {"status": "not_found", "message": "Job not found"}


@router.get("/test-cases/{journey_name}")
async def get_test_cases(journey_name: str):
    """Get merged test cases for a journey"""
    try:
        # Path to merged test cases file
        test_cases_file = DOCUMENTS_DIR / "journeys" / journey_name / f"{journey_name}_merged_test_cases.json"
        
        if not test_cases_file.exists():
            return {
                "success": False,
                "message": f"No test cases found for journey: {journey_name}",
                "test_cases": []
            }
        
        # Read and return test cases
        with open(test_cases_file, 'r') as f:
            data = json.load(f)
        
        # Flatten all test cases from different categories into a single list
        all_test_cases = []
        for category, cases in data.get("test_cases", {}).items():
            all_test_cases.extend(cases)
        
        return {
            "success": True,
            "journey_name": data.get("journey_name"),
            "total_documents": data.get("total_documents", 0),
            "test_cases": all_test_cases,
            "summary": data.get("summary", {})
        }
    
    except Exception as e:
        print(f"[ERROR] Error loading test cases: {str(e)}")
        return {
            "success": False,
            "message": f"Error loading test cases: {str(e)}",
            "test_cases": []
        }


@router.get("/journeys")
async def get_journeys():
    """Get list of all available journeys"""
    try:
        journeys_dir = DOCUMENTS_DIR / "journeys"
        
        if not journeys_dir.exists():
            return {
                "success": False,
                "message": "Journeys directory not found",
                "journeys": []
            }
        
        # Get all directories in journeys folder
        journeys = []
        for item in journeys_dir.iterdir():
            if item.is_dir():
                # Check if merged test cases file exists
                merged_file = item / f"{item.name}_merged_test_cases.json"
                has_test_cases = merged_file.exists()
                
                # Get test case count if available
                test_case_count = 0
                if has_test_cases:
                    try:
                        with open(merged_file, 'r') as f:
                            data = json.load(f)
                            test_case_count = data.get("summary", {}).get("total_test_cases", 0)
                    except:
                        pass
                
                journeys.append({
                    "name": item.name,
                    "has_test_cases": has_test_cases,
                    "test_case_count": test_case_count
                })
        
        # Sort by name
        journeys.sort(key=lambda x: x["name"])
        
        return {
            "success": True,
            "journeys": journeys,
            "total": len(journeys)
        }
    
    except Exception as e:
        print(f"[ERROR] Error loading journeys: {str(e)}")
        return {
            "success": False,
            "message": f"Error loading journeys: {str(e)}",
            "journeys": []
        }


@router.post("/reset")
async def reset_session(session_id: str = "default"):
    """Reset conversation session"""
    if session_id in conversation_states:
        del conversation_states[session_id]
    
    return {"message": "Session reset successfully"}
