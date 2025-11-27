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
    """Agent for generating test cases from parsed documents"""
    
    def __init__(self):
        self.llm = ChatOpenAI(
            model=os.getenv("DEFAULT_MODEL", "mistralai/mistral-7b-instruct:free"),
            openai_api_key=os.getenv("OPENROUTER_API_KEY"),
            openai_api_base=os.getenv("OPENROUTER_BASE_URL"),
            temperature=0.7
        )
    
    def generate_test_cases_from_document(self, document_markdown: str, document_name: str) -> Dict[str, Any]:
        """
        Generate test cases directly from full document markdown
        
        Args:
            document_markdown: Full markdown content of the document
            document_name: Name of the document for reference
            
        Returns:
            Dict containing test cases categorized by type
        """
        if not document_markdown or len(document_markdown.strip()) < 50:
            print(f"[WARNING] Document '{document_name}' is too short or empty")
            return {
                "test_cases": {
                    "sanity": [],
                    "regression": [],
                    "positive": [],
                    "negative": [],
                    "edge": []
                },
                "error": "Document content too short"
            }
        
        print(f"[INFO] Generating test cases from document: {document_name} ({len(document_markdown)} chars)")
        
        # Truncate if too long (keep within token limits)
        max_chars = 15000
        if len(document_markdown) > max_chars:
            print(f"[WARNING] Document too long ({len(document_markdown)} chars), truncating to {max_chars}")
            document_markdown = document_markdown[:max_chars] + "\n\n[... document truncated for processing ...]"
        
        system_prompt = """You are an expert QA engineer specializing in comprehensive test case generation.
Your task is to analyze requirement documents and generate thorough test cases.

CRITICAL: Your response must be ONLY valid JSON. Do not include any explanatory text, comments, or markdown.

Generate test cases in these categories:
1. Sanity - Basic smoke tests to verify core functionality works
2. Regression - Tests to ensure existing functionality isn't broken  
3. Positive - Valid input scenarios that should succeed
4. Negative - Invalid inputs that should fail gracefully with proper error handling
5. Edge - Boundary conditions, corner cases, and limit testing

Format each test case as:
{
  "id": "Unique ID like TC001",
  "title": "Brief descriptive title",
  "description": "Detailed description of what is being tested",
  "preconditions": ["List of prerequisites"],
  "steps": ["Step 1", "Step 2", "Step 3"],
  "expected_result": "What should happen",
  "priority": "high/medium/low",
  "category": "Category name"
}

Return ONLY this JSON structure:
{
  "sanity": [array of test case objects],
  "regression": [array of test case objects],
  "positive": [array of test case objects],
  "negative": [array of test case objects],
  "edge": [array of test case objects]
}"""

        user_prompt = f"""Analyze this complete requirement document and generate comprehensive test cases:

DOCUMENT: {document_name}

{document_markdown}

Generate detailed test cases covering all requirements, features, workflows, and business rules mentioned in the document.
Be thorough and specific. Each test case should be actionable and clear."""

        max_retries = 3
        retry_delay = 2
        
        for attempt in range(max_retries):
            try:
                if attempt > 0:
                    print(f"[INFO] Retry attempt {attempt + 1}/{max_retries} for document {document_name}")
                    time.sleep(retry_delay * attempt)
                
                print(f"[INFO] Calling LLM to generate test cases for {document_name}...")
                response = self.llm.invoke([
                    SystemMessage(content=system_prompt),
                    HumanMessage(content=user_prompt)
                ])
                
                print(f"[INFO] LLM response received ({len(response.content)} chars)")
                
                response_text = response.content.strip()
                
                if not response_text:
                    if attempt < max_retries - 1:
                        print(f"[WARNING] Empty response from LLM, retrying...")
                        continue
                    else:
                        return {
                            "error": "Empty response from LLM after retries",
                            "test_cases": {
                                "sanity": [],
                                "regression": [],
                                "positive": [],
                                "negative": [],
                                "edge": []
                            }
                        }
                
                # Extract JSON from response
                json_text = response_text
                
                # Remove markdown code blocks if present
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
                
                # Find JSON object boundaries
                if not json_text.startswith("{"):
                    first_brace = json_text.find("{")
                    if first_brace != -1:
                        json_text = json_text[first_brace:]
                
                if not json_text.endswith("}"):
                    last_brace = json_text.rfind("}")
                    if last_brace != -1:
                        json_text = json_text[:last_brace + 1]
                
                test_cases_data = json.loads(json_text)
                
                # Validate structure
                if not isinstance(test_cases_data, dict):
                    raise ValueError("Response is not a JSON object")
                
                # Ensure all categories exist
                for category in ["sanity", "regression", "positive", "negative", "edge"]:
                    if category not in test_cases_data:
                        test_cases_data[category] = []
                
                # Count total test cases
                total_tcs = sum(len(test_cases_data.get(cat, [])) for cat in ["sanity", "regression", "positive", "negative", "edge"])
                print(f"[SUCCESS] Generated {total_tcs} test cases for {document_name}")
                
                return {
                    "test_cases": test_cases_data,
                    "document_name": document_name,
                    "total_test_cases": total_tcs
                }
                
            except json.JSONDecodeError as e:
                if attempt < max_retries - 1:
                    print(f"[WARNING] JSON decode error, retrying: {str(e)}")
                    print(f"[DEBUG] Response preview: {response_text[:500] if 'response_text' in locals() else 'N/A'}")
                    continue
                else:
                    print(f"[ERROR] JSON decode error after {max_retries} attempts: {str(e)}")
                    return {
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
                    print(f"[WARNING] Error generating test cases, retrying: {str(e)}")
                    continue
                else:
                    print(f"[ERROR] Failed to generate test cases after {max_retries} attempts: {str(e)}")
                    return {
                        "error": str(e),
                        "test_cases": {
                            "sanity": [],
                            "regression": [],
                            "positive": [],
                            "negative": [],
                            "edge": []
                        }
                    }
    
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
        Process a document and generate test cases from full markdown content
        
        Args:
            journey_name: Name of the journey
            document_filename: Name of the document file
            parse_result: Parse result containing markdown
            document_type: Type of document (optional)
            progress_callback: Optional callback function(current_step, total_steps) for progress updates
            
        Returns:
            Dict containing all generated test cases and metadata
        """
        # Extract full markdown from parse result
        document_markdown = parse_result.get("markdown", "")
        
        if not document_markdown:
            print(f"[WARNING] No markdown found in parse result for {document_filename}")
            return {
                "journey_name": journey_name,
                "document_filename": document_filename,
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
        
        print(f"[INFO] Generating test cases from full document: {document_filename}")
        
        # Update progress - step 1: analyzing document
        if progress_callback:
            progress_callback(0, 3)
        
        # Generate test cases from full document
        result = self.generate_test_cases_from_document(document_markdown, document_filename)
        
        # Update progress - step 2: organizing test cases
        if progress_callback:
            progress_callback(1, 3)
        
        test_cases_data = result.get("test_cases", {})
        error = result.get("error")
        
        if error:
            print(f"[WARNING] Error generating test cases: {error}")
        
        # Calculate summary
        summary = {
            "total_test_cases": sum(len(test_cases_data.get(cat, [])) for cat in ["sanity", "regression", "positive", "negative", "edge"]),
            "by_category": {
                cat: len(test_cases_data.get(cat, [])) for cat in ["sanity", "regression", "positive", "negative", "edge"]
            }
        }
        
        print(f"[INFO] Generated {summary['total_test_cases']} test cases for {document_filename}")
        
        # Update progress - step 3: saving results
        if progress_callback:
            progress_callback(2, 3)
        
        # Save test cases for this document using centralized path config
        if document_type:
            save_dir = DOCUMENTS_DIR / "journeys" / journey_name / document_type
        else:
            save_dir = DOCUMENTS_DIR / "journeys" / journey_name
        
        save_dir.mkdir(parents=True, exist_ok=True)
        
        base_filename = os.path.splitext(document_filename)[0]
        test_cases_path = save_dir / f"{base_filename}_test_cases.json"
        
        final_result = {
            "journey_name": journey_name,
            "document_filename": document_filename,
            "document_type": document_type,
            "test_cases": test_cases_data,
            "summary": summary,
            "error": error
        }
        
        with open(test_cases_path, 'w') as f:
            json.dump(final_result, f, indent=2)
        
        print(f"[INFO] Test cases saved to: {test_cases_path}")
        
        return final_result
    
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
