"""
Test Case Generator Agent for creating comprehensive test cases from document chunks
"""
import os
import json
import re
import time
from typing import Dict, Any, List, Optional
from langchain_openai import ChatOpenAI
from langchain_core.messages import HumanMessage, SystemMessage
from dotenv import load_dotenv
from config import DOCUMENTS_DIR

load_dotenv()


class TestCaseGeneratorAgent:
    """Agent for generating test cases from parsed document chunks"""
    
    def __init__(self):
        self.llm = ChatOpenAI(
            model=os.getenv("DEFAULT_MODEL", "mistralai/mistral-7b-instruct:free"),
            openai_api_key=os.getenv("OPENROUTER_API_KEY"),
            openai_api_base=os.getenv("OPENROUTER_BASE_URL"),
            temperature=0.7
        )
    
    def generate_test_cases_for_chunk(self, chunk: Dict[str, Any], chunk_index: int) -> Dict[str, Any]:
        """
        Generate test cases for a single chunk
        
        Args:
            chunk: A chunk from the parse result containing markdown and metadata
            chunk_index: Index of the chunk for reference
            
        Returns:
            Dict containing test cases categorized by type
        """
        chunk_text = chunk.get("markdown", "")
        
        if not chunk_text or len(chunk_text.strip()) < 20:
            print(f"[DEBUG] Skipping chunk {chunk_index} - too short or empty (length: {len(chunk_text)})")
            return {
                "chunk_index": chunk_index,
                "test_cases": {
                    "sanity": [],
                    "regression": [],
                    "positive": [],
                    "negative": [],
                    "edge": []
                }
            }
        
        print(f"[DEBUG] Chunk {chunk_index} length: {len(chunk_text)} chars")
        
        # If chunk is very large (>4000 chars), simplify it by removing HTML tags
        if len(chunk_text) > 4000:
            print(f"[WARNING] Chunk {chunk_index} is very large ({len(chunk_text)} chars) - simplifying...")
            # Remove HTML tags for simpler processing
            import re
            chunk_text = re.sub(r'<[^>]+>', ' ', chunk_text)
            chunk_text = re.sub(r'\s+', ' ', chunk_text).strip()
            print(f"[DEBUG] Simplified chunk {chunk_index} to {len(chunk_text)} chars")
        
        system_prompt = """You are an expert QA engineer specializing in test case generation.
Your task is to analyze requirement chunks and generate comprehensive test cases.

CRITICAL: Your response must be ONLY valid JSON. Do not include any explanatory text, comments, or markdown.

For each requirement chunk, generate:
1. Sanity test cases - Basic smoke tests to verify core functionality
2. Regression test cases - Tests to ensure existing functionality isn't broken
3. Positive test cases - Valid input scenarios that should succeed
4. Negative test cases - Invalid inputs that should fail gracefully
5. Edge test cases - Boundary conditions and corner cases

Format each test case as a JSON object with:
- id: Unique identifier (e.g., "TC001")
- title: Brief descriptive title
- description: Detailed test description
- preconditions: List of preconditions
- steps: List of test steps
- expected_result: Expected outcome
- priority: high/medium/low
- category: sanity/regression/positive/negative/edge

Return ONLY this JSON structure (no other text):
{
  "sanity": [test case objects],
  "regression": [test case objects],
  "positive": [test case objects],
  "negative": [test case objects],
  "edge": [test case objects]
}"""

        user_prompt = f"""Analyze this requirement chunk and generate comprehensive test cases:

CHUNK #{chunk_index + 1}:
{chunk_text}

Generate test cases covering all categories. Be specific and actionable."""

        # Retry logic for rate limiting
        max_retries = 3
        retry_delay = 2  # seconds
        
        for attempt in range(max_retries):
            try:
                if attempt > 0:
                    print(f"[INFO] Retry attempt {attempt + 1}/{max_retries} for chunk {chunk_index}")
                    time.sleep(retry_delay * attempt)  # Exponential backoff
                
                print(f"[DEBUG] Calling LLM for chunk {chunk_index}...")
                response = self.llm.invoke([
                    SystemMessage(content=system_prompt),
                    HumanMessage(content=user_prompt)
                ])
                
                print(f"[DEBUG] LLM call successful for chunk {chunk_index}")
                
                # Parse the response
                response_text = response.content.strip()
                
                print(f"[DEBUG] LLM Response length for chunk {chunk_index}: {len(response_text)} chars")
                print(f"[DEBUG] LLM Response for chunk {chunk_index}: {response_text[:500] if response_text else '(EMPTY RESPONSE)'}...")
                
                if not response_text:
                    if attempt < max_retries - 1:
                        print(f"[WARNING] Empty response from LLM for chunk {chunk_index}, retrying...")
                        continue
                    else:
                        print(f"[ERROR] Empty response from LLM for chunk {chunk_index} after {max_retries} attempts")
                        print(f"[ERROR] Chunk length was: {len(chunk_text)} chars")
                        return {
                            "chunk_index": chunk_index,
                            "error": "Empty response from LLM after retries - possible rate limit or model error",
                            "test_cases": {
                                "sanity": [],
                                "regression": [],
                                "positive": [],
                                "negative": [],
                                "edge": []
                            }
                        }
                
                # Try to extract JSON from the response
                json_text = response_text
                
                # Remove any markdown code blocks
                if "```json" in response_text:
                    json_start = response_text.find("```json") + 7
                    json_end = response_text.find("```", json_start)
                    if json_end > json_start:
                        json_text = response_text[json_start:json_end].strip()
                elif "```" in response_text:
                    json_start = response_text.find("```") + 3
                    json_end = response_text.find("```", json_start)
                    if json_end > json_start:
                        json_text = response_text[json_start:json_end].strip()
                
                # Try to find JSON object by looking for { and }
                if not json_text.startswith("{"):
                    first_brace = json_text.find("{")
                    if first_brace != -1:
                        json_text = json_text[first_brace:]
                
                if not json_text.endswith("}"):
                    last_brace = json_text.rfind("}")
                    if last_brace != -1:
                        json_text = json_text[:last_brace + 1]
                
                print(f"[DEBUG] Extracted JSON for chunk {chunk_index}: {json_text[:300] if json_text else '(EMPTY)'}...")
                
                test_cases = json.loads(json_text)
                
                # Successfully parsed JSON, return result
                return {
                    "chunk_index": chunk_index,
                    "chunk_preview": chunk_text[:200] + "..." if len(chunk_text) > 200 else chunk_text,
                    "test_cases": test_cases
                }
                
            except json.JSONDecodeError as e:
                if attempt < max_retries - 1:
                    print(f"[WARNING] JSON decode error for chunk {chunk_index}, retrying: {str(e)}")
                    continue
                else:
                    print(f"[ERROR] JSON decode error for chunk {chunk_index} after {max_retries} attempts: {str(e)}")
                    print(f"[ERROR] Response text: {response_text[:1000] if 'response_text' in locals() else 'N/A'}")
                    return {
                        "chunk_index": chunk_index,
                        "error": f"JSON decode error: {str(e)}",
                        "test_cases": {
                            "sanity": [],
                            "regression": [],
                            "positive": [],
                            "negative": [],
                            "edge": []
                        }
                    }
            except Exception as e:
                if attempt < max_retries - 1:
                    print(f"[WARNING] Error generating test cases for chunk {chunk_index}, retrying: {str(e)}")
                    continue
                else:
                    print(f"[ERROR] Failed to generate test cases for chunk {chunk_index} after {max_retries} attempts: {str(e)}")
                    print(f"[ERROR] Exception type: {type(e).__name__}")
                    return {
                        "chunk_index": chunk_index,
                        "error": str(e),
                        "test_cases": {
                            "sanity": [],
                            "regression": [],
                            "positive": [],
                            "negative": [],
                            "edge": []
                        }
                    }
    
    def merge_test_cases(self, all_chunk_results: List[Dict[str, Any]]) -> Dict[str, List]:
        """
        Merge test cases from all chunks, removing duplicates and organizing by category
        
        Args:
            all_chunk_results: List of test case results from all chunks
            
        Returns:
            Merged test cases organized by category
        """
        merged = {
            "sanity": [],
            "regression": [],
            "positive": [],
            "negative": [],
            "edge": []
        }
        
        test_case_counter = 1
        seen_titles = set()
        
        for chunk_result in all_chunk_results:
            test_cases = chunk_result.get("test_cases", {})
            
            for category in ["sanity", "regression", "positive", "negative", "edge"]:
                cases = test_cases.get(category, [])
                
                for tc in cases:
                    title = tc.get("title", "")
                    
                    # Skip duplicates based on title similarity
                    if title and title.lower() not in seen_titles:
                        # Assign new ID
                        tc["id"] = f"TC{test_case_counter:03d}"
                        tc["source_chunk"] = chunk_result.get("chunk_index")
                        
                        merged[category].append(tc)
                        seen_titles.add(title.lower())
                        test_case_counter += 1
        
        return merged
    
    def process_document(
        self,
        journey_name: str,
        document_filename: str,
        parse_result: Dict[str, Any],
        document_type: Optional[str] = None,
        progress_callback: Optional[callable] = None
    ) -> Dict[str, Any]:
        """
        Process a document and generate test cases for all chunks
        
        Args:
            journey_name: Name of the journey
            document_filename: Name of the document file
            parse_result: Parse result containing chunks
            document_type: Type of document (optional)
            progress_callback: Optional callback function(chunk_index, total_chunks) for progress updates
            
        Returns:
            Dict containing all generated test cases and metadata
        """
        chunks = parse_result.get("chunks", [])
        
        if not chunks:
            print(f"[WARNING] No chunks found in parse result for {document_filename}")
            return {
                "journey_name": journey_name,
                "document_filename": document_filename,
                "total_chunks": 0,
                "test_cases": {
                    "sanity": [],
                    "regression": [],
                    "positive": [],
                    "negative": [],
                    "edge": []
                },
                "summary": {
                    "total_test_cases": 0,
                    "by_category": {
                        "sanity": 0,
                        "regression": 0,
                        "positive": 0,
                        "negative": 0,
                        "edge": 0
                    }
                }
            }
        
        print(f"[INFO] Generating test cases for {len(chunks)} chunks from {document_filename}")
        
        # Generate test cases for each chunk
        chunk_results = []
        for i, chunk in enumerate(chunks):
            print(f"[INFO] Processing chunk {i + 1}/{len(chunks)}...")
            
            # Call progress callback if provided
            if progress_callback:
                progress_callback(i, len(chunks))
            
            result = self.generate_test_cases_for_chunk(chunk, i)
            chunk_results.append(result)
        
        # Merge all test cases
        merged_test_cases = self.merge_test_cases(chunk_results)
        
        # Calculate summary
        summary = {
            "total_test_cases": sum(len(merged_test_cases[cat]) for cat in merged_test_cases),
            "by_category": {
                cat: len(merged_test_cases[cat]) for cat in merged_test_cases
            }
        }
        
        print(f"[INFO] Generated {summary['total_test_cases']} test cases")
        
        # Get absolute path to backend directory
        # Save test cases for this document using centralized path config
        if document_type:
            save_dir = DOCUMENTS_DIR / "journeys" / journey_name / document_type
        else:
            save_dir = DOCUMENTS_DIR / "journeys" / journey_name
        
        save_dir.mkdir(parents=True, exist_ok=True)
        
        base_filename = os.path.splitext(document_filename)[0]
        test_cases_path = save_dir / f"{base_filename}_test_cases.json"
        
        result = {
            "journey_name": journey_name,
            "document_filename": document_filename,
            "document_type": document_type,
            "total_chunks": len(chunks),
            "test_cases": merged_test_cases,
            "chunk_results": chunk_results,
            "summary": summary
        }
        
        with open(test_cases_path, 'w') as f:
            json.dump(result, f, indent=2)
        
        print(f"[INFO] Test cases saved to: {test_cases_path}")
        
        return result
    
    def merge_journey_test_cases(self, journey_name: str) -> Dict[str, Any]:
        """
        Merge all test cases from all documents in a journey
        
        Args:
            journey_name: Name of the journey
            
        Returns:
            Merged test cases for the entire journey
        """
        journey_path = DOCUMENTS_DIR / "journeys" / journey_name
        
        if not journey_path.exists():
            return {
                "journey_name": journey_name,
                "error": "Journey not found"
            }
        
        all_test_cases = []
        
        # Walk through all subdirectories
        for root, dirs, files in os.walk(str(journey_path)):
            for file in files:
                if file.endswith("_test_cases.json"):
                    file_path = os.path.join(root, file)
                    try:
                        with open(file_path, 'r') as f:
                            doc_test_cases = json.load(f)
                            all_test_cases.append(doc_test_cases)
                    except Exception as e:
                        print(f"[ERROR] Failed to load {file_path}: {str(e)}")
        
        if not all_test_cases:
            return {
                "journey_name": journey_name,
                "total_documents": 0,
                "test_cases": {
                    "sanity": [],
                    "regression": [],
                    "positive": [],
                    "negative": [],
                    "edge": []
                },
                "summary": {
                    "total_test_cases": 0,
                    "by_category": {
                        "sanity": 0,
                        "regression": 0,
                        "positive": 0,
                        "negative": 0,
                        "edge": 0
                    }
                }
            }
        
        # Merge test cases from all documents
        merged = {
            "sanity": [],
            "regression": [],
            "positive": [],
            "negative": [],
            "edge": []
        }
        
        test_case_counter = 1
        seen_titles = set()
        
        for doc_result in all_test_cases:
            test_cases = doc_result.get("test_cases", {})
            
            for category in ["sanity", "regression", "positive", "negative", "edge"]:
                cases = test_cases.get(category, [])
                
                for tc in cases:
                    title = tc.get("title", "")
                    
                    # Skip duplicates
                    if title and title.lower() not in seen_titles:
                        tc["id"] = f"TC{test_case_counter:03d}"
                        tc["source_document"] = doc_result.get("document_filename")
                        
                        merged[category].append(tc)
                        seen_titles.add(title.lower())
                        test_case_counter += 1
        
        summary = {
            "total_test_cases": sum(len(merged[cat]) for cat in merged),
            "by_category": {
                cat: len(merged[cat]) for cat in merged
            }
        }
        
        # Save merged test cases
        merged_path = journey_path / f"{journey_name}_merged_test_cases.json"
        
        result = {
            "journey_name": journey_name,
            "total_documents": len(all_test_cases),
            "test_cases": merged,
            "summary": summary
        }
        
        with open(merged_path, 'w') as f:
            json.dump(result, f, indent=2)
        
        print(f"[INFO] Merged test cases saved to: {merged_path}")
        
        return result


def create_test_case_generator_agent() -> TestCaseGeneratorAgent:
    """Factory function to create test case generator agent"""
    return TestCaseGeneratorAgent()
