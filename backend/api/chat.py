from fastapi import APIRouter, UploadFile, File, Form
from pydantic import BaseModel
from agents.orchestrator import create_orchestrator_graph
from agents.landing_ai_agent import create_landing_ai_agent
from agents.test_case_generator_agent import create_test_case_generator_agent
from agents.rag_agent import create_rag_agent
from langchain_core.messages import HumanMessage, AIMessage
from config import DOCUMENTS_DIR
import os
import shutil
import asyncio
import json
from typing import Optional, Dict, Any, List

router = APIRouter()

orchestrator_graph = create_orchestrator_graph()
landing_ai_agent = create_landing_ai_agent()
test_case_generator = create_test_case_generator_agent()
rag_agent = create_rag_agent()

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
        if state["conversation_step"] == "initial" or not state["messages"]:
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
    
    # Clean up markdown formatting
    response_text = response_text.replace("**", "")  # Remove bold
    response_text = response_text.replace("__", "")  # Remove underline
    response_text = response_text.replace("*", "")   # Remove italic (single asterisk)
    response_text = response_text.replace("_", " ")  # Replace underscores with spaces
    
    return ChatResponse(
        response=response_text,
        conversation_step=result.get("conversation_step", "initial"),
        journey_name=result.get("journey_name"),
        document_type=result.get("document_type")
    )


async def generate_test_cases_async(
    job_id: str,
    filename: str,
    journey_name: str,
    parse_result: Dict[str, Any],
    document_type: Optional[str],
    session_id: str
):
    """Async task to generate test cases in background"""
    try:
        processing_status[job_id]["stage"] = "generating_tests"
        processing_status[job_id]["message"] = f"Generating test cases from document..."
        
        # Progress callback to update status
        def update_progress(current_step: int, total_steps: int):
            steps = ["Analyzing document", "Organizing test cases", "Saving results"]
            if current_step < len(steps):
                processing_status[job_id]["message"] = f"{steps[current_step]}..."
        
        # Generate test cases from full document
        print(f"[INFO] Starting async test case generation for {filename}")
        test_case_result = await asyncio.to_thread(
            test_case_generator.process_document,
            journey_name=journey_name,
            document_filename=filename,
            parse_result=parse_result,
            document_type=document_type,
            progress_callback=update_progress
        )
        
        total_test_cases = test_case_result.get("summary", {}).get("total_test_cases", 0)
        print(f"[INFO] Generated {total_test_cases} test cases for {filename}")
        
        processing_status[job_id]["stage"] = "merging"
        processing_status[job_id]["message"] = f"Generated {total_test_cases} test cases. Merging journey results..."
        
        # Merge test cases for entire journey
        print(f"[INFO] Merging all test cases for journey: {journey_name}")
        merged_result = await asyncio.to_thread(
            test_case_generator.merge_journey_test_cases,
            journey_name
        )
        total_merged_test_cases = merged_result.get("summary", {}).get("total_test_cases", 0)
        print(f"[INFO] Total test cases for journey '{journey_name}': {total_merged_test_cases}")
        
        # Update status to completed
        processing_status[job_id] = {
            "status": "completed",
            "stage": "done",
            "message": f"Processing complete!\n\nDocument: {filename}\nTest cases generated: {total_test_cases}\nTotal journey test cases: {total_merged_test_cases}",
            "test_cases": total_test_cases,
            "total_journey_test_cases": total_merged_test_cases
        }
        
        # Update conversation state
        if session_id in conversation_states:
            conversation_states[session_id]["conversation_step"] = "document_uploaded"
        
    except Exception as e:
        error_msg = f"Error generating test cases: {str(e)}"
        print(f"[ERROR] Test case generation failed: {str(e)}")
        processing_status[job_id] = {
            "status": "failed",
            "stage": "error",
            "message": error_msg,
            "error": str(e)
        }


async def process_document_async(
    file_path: str,
    filename: str,
    journey_name: str,
    document_type: Optional[str],
    session_id: str
):
    """Async task to parse document and index into Pinecone"""
    job_id = f"{session_id}_{filename}"
    
    try:
        processing_status[job_id] = {
            "status": "processing",
            "stage": "parsing",
            "message": "Parsing document with Landing AI..."
        }
        
        # Process document with Landing AI (parsing only - fast operation)
        # Run in thread pool to avoid blocking
        landing_ai_result = await asyncio.to_thread(
            landing_ai_agent.process_document,
            document_path=file_path,
            journey_name=journey_name,
            document_type=document_type
        )
        
        chunks_count = len(landing_ai_result.get("chunks", []))
        
        # Index into FAISS for RAG
        processing_status[job_id]["stage"] = "indexing"
        processing_status[job_id]["message"] = "Indexing document into FAISS vector store..."
        
        print(f"[INFO] Indexing document into FAISS: {filename}")
        index_result = await asyncio.to_thread(
            rag_agent.index_document,
            journey_name=journey_name,
            document_filename=filename,
            parse_result=landing_ai_result,
            document_type=document_type
        )
        
        indexed_chunks = index_result.get("indexed_chunks", 0)
        print(f"[INFO] Indexed {indexed_chunks} chunks into FAISS for journey '{journey_name}'")
        
        # Update status to completed (parsing only)
        processing_status[job_id] = {
            "status": "completed",
            "stage": "parsed",
            "message": f"Document processed successfully!\n\nParsed {chunks_count} chunks\nIndexed {indexed_chunks} embeddings\n\nYou can now:\n- Generate test cases from Test Cases view\n- Ask questions in RAG Assistant",
            "chunks_count": chunks_count,
            "indexed_chunks": indexed_chunks
        }
        
        print(f"[INFO] Document parsed and indexed successfully: {chunks_count} chunks, {indexed_chunks} vectors.")
        
    except Exception as e:
        error_msg = f"Error processing document: {str(e)}"
        print(f"[ERROR] Background processing failed: {str(e)}")
        processing_status[job_id] = {
            "status": "failed",
            "stage": "error",
            "message": error_msg,
            "error": str(e)
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
        process_document_async(
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
        "message": "✅ Got your file. Document is being parsed now. Once complete, you can generate test cases from the Test Cases view.",
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
                
                # Check for parsed documents
                parse_files = list(item.glob("**/*_parse_result.json"))
                has_parsed_docs = len(parse_files) > 0
                
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
                    "has_parsed_docs": has_parsed_docs,
                    "parsed_doc_count": len(parse_files),
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


class ResetRequest(BaseModel):
    session_id: Optional[str] = "default"

@router.post("/reset")
async def reset_session(request: ResetRequest):
    """Reset conversation session"""
    session_id = request.session_id
    if session_id in conversation_states:
        del conversation_states[session_id]
    
    return {"message": "Session reset successfully", "success": True}


@router.post("/generate-test-cases/{journey_name}")
async def generate_test_cases_for_journey(journey_name: str):
    """Generate test cases for all parsed documents in a journey"""
    try:
        journey_path = DOCUMENTS_DIR / "journeys" / journey_name
        
        if not journey_path.exists():
            return {
                "success": False,
                "message": f"Journey '{journey_name}' not found"
            }
        
        # Find all parse result files in the journey
        parse_files = list(journey_path.glob("**/*_parse_result.json"))
        
        if not parse_files:
            return {
                "success": False,
                "message": f"No parsed documents found in journey '{journey_name}'. Please upload and parse documents first."
            }
        
        # Create a unique job ID for this generation
        job_id = f"generate_{journey_name}_{asyncio.get_event_loop().time()}"
        
        processing_status[job_id] = {
            "status": "processing",
            "stage": "starting",
            "message": f"Starting test case generation for {len(parse_files)} document(s)...",
            "total_documents": len(parse_files),
            "processed_documents": 0
        }
        
        # Start async test case generation
        asyncio.create_task(
            generate_all_test_cases_for_journey(
                job_id=job_id,
                journey_name=journey_name,
                parse_files=parse_files
            )
        )
        
        return {
            "success": True,
            "message": f"Test case generation started for {len(parse_files)} document(s)",
            "job_id": job_id,
            "total_documents": len(parse_files)
        }
        
    except Exception as e:
        print(f"[ERROR] Error starting test case generation: {str(e)}")
        return {
            "success": False,
            "message": f"Error: {str(e)}"
        }


async def generate_all_test_cases_for_journey(
    job_id: str,
    journey_name: str,
    parse_files: list
):
    """Generate test cases for all documents in a journey"""
    try:
        total_docs = len(parse_files)
        
        for idx, parse_file in enumerate(parse_files):
            # Update progress
            processing_status[job_id]["processed_documents"] = idx
            processing_status[job_id]["message"] = f"Generating test cases for document {idx + 1}/{total_docs}..."
            
            # Load parse result
            with open(parse_file, 'r') as f:
                parse_result = json.load(f)
            
            # Extract document filename from parse file name
            filename = parse_file.name.replace("_parse_result.json", ".pdf")
            
            # Determine document type from folder structure
            document_type = None
            if parse_file.parent != DOCUMENTS_DIR / "journeys" / journey_name:
                document_type = parse_file.parent.name
            
            # Progress callback
            def update_progress(current_step: int, total_steps: int):
                steps = ["Analyzing", "Organizing", "Saving"]
                if current_step < len(steps):
                    processing_status[job_id]["message"] = f"Document {idx + 1}/{total_docs} - {steps[current_step]}..."
            
            # Generate test cases for this document
            await asyncio.to_thread(
                test_case_generator.process_document,
                journey_name=journey_name,
                document_filename=filename,
                parse_result=parse_result,
                document_type=document_type,
                progress_callback=update_progress
            )
        
        # Merge all test cases
        processing_status[job_id]["stage"] = "merging"
        processing_status[job_id]["message"] = "Merging all test cases..."
        
        merged_result = await asyncio.to_thread(
            test_case_generator.merge_journey_test_cases,
            journey_name
        )
        
        total_test_cases = merged_result.get("summary", {}).get("total_test_cases", 0)
        
        # Update to completed
        processing_status[job_id] = {
            "status": "completed",
            "stage": "done",
            "message": f"Test case generation complete!\n\nProcessed {total_docs} document(s)\nGenerated {total_test_cases} test cases",
            "total_documents": total_docs,
            "total_test_cases": total_test_cases
        }
        
        print(f"[INFO] Test case generation completed for journey '{journey_name}': {total_test_cases} test cases")
        
    except Exception as e:
        error_msg = f"Error generating test cases: {str(e)}"
        print(f"[ERROR] {error_msg}")
        processing_status[job_id] = {
            "status": "failed",
            "stage": "error",
            "message": error_msg,
            "error": str(e)
        }


# RAG Endpoints

class RAGQueryRequest(BaseModel):
    question: str
    journey_name: Optional[str] = None
    top_k: int = 5


class RAGQueryResponse(BaseModel):
    success: bool
    answer: str
    evidence: List[Dict[str, Any]]
    question: str
    sources_count: int = 0


@router.post("/rag/query", response_model=RAGQueryResponse)
async def rag_query(request: RAGQueryRequest):
    """Query the RAG system with a question"""
    try:
        result = await asyncio.to_thread(
            rag_agent.query,
            question=request.question,
            journey_name=request.journey_name,
            top_k=request.top_k
        )
        
        return RAGQueryResponse(
            success=result.get("success", False),
            answer=result.get("answer", ""),
            evidence=result.get("evidence", []),
            question=result.get("question", request.question),
            sources_count=result.get("sources_count", 0)
        )
    except Exception as e:
        print(f"[ERROR] RAG query failed: {str(e)}")
        return RAGQueryResponse(
            success=False,
            answer=f"Error processing question: {str(e)}",
            evidence=[],
            question=request.question,
            sources_count=0
        )


@router.get("/rag/stats")
async def rag_stats(journey_name: Optional[str] = None):
    """Get RAG index statistics"""
    try:
        stats = await asyncio.to_thread(
            rag_agent.get_index_stats,
            journey_name=journey_name
        )
        return stats
    except Exception as e:
        print(f"[ERROR] Failed to get RAG stats: {str(e)}")
        return {
            "success": False,
            "message": str(e)
        }
