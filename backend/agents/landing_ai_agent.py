"""
Landing AI Agent for document parsing and extraction
"""
import os
import requests
import json
from typing import Dict, Any, Optional
from dotenv import load_dotenv

load_dotenv()

LANDING_AI_API_KEY = os.getenv("LANDINGAI_API_KEY")
LANDING_AI_BASE_URL = "https://api.va.landing.ai/v1/ade"


class LandingAIAgent:
    """Agent for parsing documents and extracting structured data using Landing AI"""
    
    def __init__(self, api_key: Optional[str] = None):
        self.api_key = api_key or LANDING_AI_API_KEY
        self.base_url = LANDING_AI_BASE_URL
        
    def parse_document(self, document_path: str, model: str = "dpt-2-latest") -> Dict[str, Any]:
        """
        Parse a PDF document using Landing AI Parse API
        
        Args:
            document_path: Path to the PDF document
            model: Model to use for parsing (default: dpt-2-latest)
            
        Returns:
            Dict containing markdown, chunks, splits, grounding, and metadata
        """
        url = f"{self.base_url}/parse"
        headers = {
            "Authorization": f"Bearer {self.api_key}"
        }
        
        with open(document_path, 'rb') as doc_file:
            files = {
                'document': doc_file,
                'model': (None, model)
            }
            
            response = requests.post(url, headers=headers, files=files)
            response.raise_for_status()
            
        return response.json()
    
    def extract_data(
        self, 
        parse_result: Dict[str, Any],
        schema: Optional[Dict[str, Any]] = None,
        model: str = "extract-latest"
    ) -> Dict[str, Any]:
        """
        Extract structured data using Landing AI Extract API
        
        Args:
            parse_result: The complete parse result from parse_document
            schema: JSON schema defining what to extract (if None, uses a default schema)
            model: Model to use for extraction (default: extract-latest)
            
        Returns:
            Dict containing extraction results, metadata, and any errors
        """
        url = f"{self.base_url}/extract"
        headers = {
            "Authorization": f"Bearer {self.api_key}"
        }
        
        # Extract markdown from parse result
        markdown = parse_result.get("markdown", "")
        
        if not markdown:
            raise ValueError("No markdown found in parse result")
        
        # Use default schema if none provided
        if schema is None:
            schema = {
                "type": "object",
                "properties": {
                    "key_entities": {
                        "type": "array",
                        "description": "List of important entities, names, organizations, or concepts mentioned in the document",
                        "items": {"type": "string"}
                    },
                    "requirements": {
                        "type": "array",
                        "description": "List of requirements, features, or functionalities described in the document",
                        "items": {"type": "string"}
                    },
                    "actions": {
                        "type": "array",
                        "description": "List of user actions, workflows, or processes described",
                        "items": {"type": "string"}
                    },
                    "business_rules": {
                        "type": "array",
                        "description": "List of business rules, validations, or constraints mentioned",
                        "items": {"type": "string"}
                    },
                    "data_fields": {
                        "type": "array",
                        "description": "List of data fields, attributes, or parameters mentioned",
                        "items": {"type": "string"}
                    }
                },
                "required": ["key_entities", "requirements", "actions", "business_rules", "data_fields"]
            }
        
        # Send markdown, parse_result, and schema
        files = {
            'markdown': (None, markdown),
            'parse_result': ('parse_result.json', json.dumps(parse_result), 'application/json'),
            'schema': (None, json.dumps(schema)),
            'model': (None, model)
        }
        
        response = requests.post(url, headers=headers, files=files)
        
        # Print detailed error for debugging
        if response.status_code != 200:
            print(f"[ERROR] Extract API Status: {response.status_code}")
            print(f"[ERROR] Extract API Response: {response.text}")
        
        response.raise_for_status()
        
        return response.json()
    
    def process_document(
        self,
        document_path: str,
        journey_name: str,
        document_type: Optional[str] = None
    ) -> Dict[str, Any]:
        """
        Complete workflow: Parse document, extract data using parse result as schema, and save results
        
        Args:
            document_path: Path to the PDF document
            journey_name: Name of the journey
            document_type: Type of document (addendum, annexture, email, other)
            
        Returns:
            Dict containing parse results, extraction results, and file paths
        """
        # Step 1: Parse the document
        parse_result = self.parse_document(document_path)
        
        # Determine save directory
        if document_type:
            save_dir = f"documents/journeys/{journey_name}/{document_type}"
        else:
            save_dir = f"documents/journeys/{journey_name}"
        
        os.makedirs(save_dir, exist_ok=True)
        
        # Get base filename without extension
        base_filename = os.path.splitext(os.path.basename(document_path))[0]
        
        # Step 2: Save parse result
        parse_result_path = os.path.join(save_dir, f"{base_filename}_parse_result.json")
        with open(parse_result_path, 'w') as f:
            json.dump(parse_result, f, indent=2)
        
        result = {
            "parse_result": parse_result,
            "parse_result_path": parse_result_path,
            "markdown": parse_result.get("markdown", ""),
            "chunks": parse_result.get("chunks", []),
            "metadata": parse_result.get("metadata", {})
        }
        
        # Step 3: Extract data using parse result as schema (mandatory)
        if parse_result.get("markdown"):
            try:
                print(f"[DEBUG] Calling extract API with parse result...")
                extraction_result = self.extract_data(
                    parse_result=parse_result
                )
                
                print(f"[DEBUG] Extract API response received: {extraction_result.keys() if isinstance(extraction_result, dict) else type(extraction_result)}")
                
                # Save extraction result
                extraction_result_path = os.path.join(save_dir, f"{base_filename}_extraction_result.json")
                with open(extraction_result_path, 'w') as f:
                    json.dump(extraction_result, f, indent=2)
                
                print(f"[DEBUG] Extraction result saved to: {extraction_result_path}")
                
                result["extraction_result"] = extraction_result
                result["extraction_result_path"] = extraction_result_path
            except Exception as e:
                print(f"[ERROR] Extract API failed: {str(e)}")
                print(f"[ERROR] Error type: {type(e).__name__}")
                if hasattr(e, 'response'):
                    print(f"[ERROR] Response status: {e.response.status_code}")
                    print(f"[ERROR] Response body: {e.response.text}")
                result["extraction_error"] = str(e)
        else:
            print(f"[WARNING] No markdown found in parse result, skipping extraction")
        
        return result


def create_landing_ai_agent() -> LandingAIAgent:
    """Factory function to create Landing AI agent"""
    return LandingAIAgent()
