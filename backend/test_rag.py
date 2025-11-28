#!/usr/bin/env python3
"""
Test script for RAG system with FAISS
"""
import json
import os
from agents.rag_agent import create_rag_agent

def test_rag_system():
    print("=== Testing RAG System with FAISS ===\n")
    
    # Initialize RAG agent
    print("1. Initializing RAG agent...")
    rag = create_rag_agent()
    print("   ✓ RAG agent initialized\n")
    
    # Load a sample parse result
    print("2. Loading sample document...")
    parse_result_path = "/Users/spartan/Documents/TraceQA-272/documents/journeys/A/Arshan_Bhanage_Resume (14)_parse_result.json"
    
    with open(parse_result_path, 'r') as f:
        parse_result = json.load(f)
    
    print(f"   ✓ Loaded parse result from journey A\n")
    
    # Index the document
    print("3. Indexing document into FAISS...")
    result = rag.index_document(
        journey_name="A",
        document_filename="Arshan_Bhanage_Resume (14).pdf",
        parse_result=parse_result,
        document_type="resume"
    )
    
    if result["success"]:
        print(f"   ✓ Successfully indexed {result['indexed_chunks']} chunks\n")
    else:
        print(f"   ✗ Failed to index: {result['message']}\n")
        return
    
    # Get stats
    print("4. Getting index statistics...")
    stats = rag.get_index_stats(journey_name="A")
    print(f"   Journey: {stats.get('journey_name', 'N/A')}")
    print(f"   Total vectors: {stats.get('total_vectors', 0)}")
    print(f"   Status: {stats.get('status', 'unknown')}\n")
    
    # Query the system
    print("5. Querying the RAG system...")
    question = "What technologies does Arshan know?"
    print(f"   Question: {question}")
    
    response = rag.query(
        question=question,
        journey_name="A",
        top_k=3
    )
    
    if response["success"]:
        print(f"\n   Answer: {response['answer']}\n")
        print(f"   Evidence ({len(response['evidence'])} sources):")
        for i, evidence in enumerate(response['evidence'], 1):
            print(f"     {i}. {evidence['document']} (score: {evidence['score']:.4f})")
    else:
        print(f"   ✗ Query failed: {response['answer']}\n")
    
    print("\n=== Test Complete ===")

if __name__ == "__main__":
    test_rag_system()
