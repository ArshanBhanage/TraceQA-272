"""
RAG Agent for answering questions using document embeddings stored in FAISS
"""
import os
import json
import pickle
import re
import faiss
import numpy as np
from typing import Dict, Any, List, Optional
from sentence_transformers import SentenceTransformer
from langchain_openai import ChatOpenAI
from langchain_core.messages import HumanMessage, SystemMessage
from dotenv import load_dotenv
from config import DOCUMENTS_DIR
import logging

load_dotenv()

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)


class RAGAgent:
    """Agent for RAG-based question answering using FAISS vector store"""
    
    def __init__(self):
        # Initialize embeddings model (384 dimensions for all-MiniLM-L6-v2)
        # Lighter model that's faster and more stable
        self.embedding_model = SentenceTransformer(
            'sentence-transformers/all-MiniLM-L6-v2',
        )
        self.dimension = 384
        
        # Initialize LLM for answering
        self.llm = ChatOpenAI(
            model=os.getenv("DEFAULT_MODEL", "mistralai/mistral-7b-instruct:free"),
            openai_api_key=os.getenv("OPENROUTER_API_KEY"),
            openai_api_base=os.getenv("OPENROUTER_BASE_URL"),
            temperature=0.3
        )
        
        # Directory to store FAISS indexes
        self.faiss_dir = os.path.join(DOCUMENTS_DIR, "faiss_indexes")
        os.makedirs(self.faiss_dir, exist_ok=True)
        
        # Cache for loaded indexes
        self.loaded_indexes: Dict[str, faiss.IndexFlatIP] = {}
        self.loaded_metadata: Dict[str, List[Dict[str, Any]]] = {}
        
        logger.info(f"RAG Agent initialized. FAISS indexes stored in: {self.faiss_dir}")
    
    def _get_index_path(self, journey_name: str) -> str:
        """Get the file path for a journey's FAISS index"""
        return os.path.join(self.faiss_dir, f"{journey_name}_faiss.index")
    
    def _get_metadata_path(self, journey_name: str) -> str:
        """Get the file path for a journey's metadata"""
        return os.path.join(self.faiss_dir, f"{journey_name}_metadata.pkl")
    
    def _strip_html(self, text: str) -> str:
        """Remove HTML tags from text"""
        # Remove HTML tags
        text = re.sub(r'<[^>]+>', '', text)
        # Replace common HTML entities
        text = text.replace('&nbsp;', ' ')
        text = text.replace('&lt;', '<')
        text = text.replace('&gt;', '>')
        text = text.replace('&amp;', '&')
        text = text.replace('&quot;', '"')
        # Clean up extra whitespace
        text = re.sub(r'\s+', ' ', text)
        return text.strip()
    
    def _load_index(self, journey_name: str) -> Optional[faiss.IndexFlatIP]:
        """Load existing FAISS index for the journey"""
        if journey_name in self.loaded_indexes:
            return self.loaded_indexes[journey_name]
        
        index_path = self._get_index_path(journey_name)
        metadata_path = self._get_metadata_path(journey_name)
        
        if os.path.exists(index_path) and os.path.exists(metadata_path):
            logger.info(f"Loading existing FAISS index for journey: {journey_name}")
            
            # Load FAISS index
            index = faiss.read_index(index_path)
            
            # Load metadata
            with open(metadata_path, 'rb') as f:
                metadata = pickle.load(f)
            
            self.loaded_indexes[journey_name] = index
            self.loaded_metadata[journey_name] = metadata
            
            logger.info(f"Loaded index with {index.ntotal} vectors")
            return index
        
        logger.info(f"No existing index for journey: {journey_name}")
        return None
    
    def index_document(
        self,
        journey_name: str,
        document_filename: str,
        parse_result: Dict[str, Any],
        document_type: Optional[str] = None
    ) -> Dict[str, Any]:
        """
        Index document chunks into FAISS for the specific journey
        
        Args:
            journey_name: Name of the journey
            document_filename: Name of the document
            parse_result: Parse result containing markdown and chunks
            document_type: Type of document (optional)
            
        Returns:
            Dict with indexing results
        """
        try:
            # Get full markdown
            markdown = parse_result.get("markdown", "")
            chunks = parse_result.get("chunks", [])
            
            if not markdown:
                return {
                    "success": False,
                    "message": "No markdown content found",
                    "indexed_chunks": 0
                }
            
            # Split markdown into chunks if no chunks provided
            if not chunks:
                # Simple chunking by paragraphs
                paragraphs = [p.strip() for p in markdown.split('\n\n') if p.strip()]
                chunks = [{"markdown": p, "index": i} for i, p in enumerate(paragraphs)]
            
            # Prepare texts and metadata
            texts = []
            metadata_list = []
            
            for i, chunk in enumerate(chunks):
                chunk_text = chunk.get("markdown", "")
                
                if not chunk_text or len(chunk_text.strip()) < 20:
                    continue
                
                # Strip HTML from text
                clean_text = self._strip_html(chunk_text)
                
                texts.append(clean_text)
                metadata_list.append({
                    "journey_name": journey_name,
                    "document_filename": document_filename,
                    "document_type": document_type or "general",
                    "chunk_index": i,
                    "text": clean_text,
                    "text_preview": clean_text[:500]
                })
            
            if not texts:
                return {
                    "success": False,
                    "message": "No valid text chunks to index",
                    "indexed_chunks": 0
                }
            
            logger.info(f"Generating embeddings for {len(texts)} chunks...")
            
            # Generate embeddings using SentenceTransformer
            embeddings = self.embedding_model.encode(
                texts,
                convert_to_numpy=True,
                show_progress_bar=False
            ).astype('float32')
            
            # Normalize embeddings for cosine similarity (using IndexFlatIP)
            faiss.normalize_L2(embeddings)
            
            # Load existing index or create new one
            index = self._load_index(journey_name)
            existing_metadata = self.loaded_metadata.get(journey_name, [])
            
            if index is None:
                # Create new FAISS index with IndexFlatIP for cosine similarity
                logger.info(f"Creating new FAISS index for journey: {journey_name}")
                index = faiss.IndexFlatIP(self.dimension)
                existing_metadata = []
            else:
                logger.info(f"Adding to existing FAISS index for journey: {journey_name}")
            
            # Add embeddings to index
            index.add(embeddings)
            
            # Combine metadata
            all_metadata = existing_metadata + metadata_list
            
            # Save index and metadata
            index_path = self._get_index_path(journey_name)
            metadata_path = self._get_metadata_path(journey_name)
            
            faiss.write_index(index, index_path)
            
            with open(metadata_path, 'wb') as f:
                pickle.dump(all_metadata, f)
            
            # Update cache
            self.loaded_indexes[journey_name] = index
            self.loaded_metadata[journey_name] = all_metadata
            
            logger.info(f"Successfully indexed {len(texts)} chunks for {document_filename}")
            logger.info(f"Total vectors in journey '{journey_name}': {index.ntotal}")
            
            return {
                "success": True,
                "message": f"Successfully indexed {len(texts)} chunks",
                "indexed_chunks": len(texts),
                "total_vectors": index.ntotal,
                "journey_name": journey_name,
                "document_filename": document_filename
            }
            
        except Exception as e:
            logger.error(f"Failed to index document: {str(e)}", exc_info=True)
            return {
                "success": False,
                "message": f"Error: {str(e)}",
                "indexed_chunks": 0
            }
    
    def query(
        self,
        question: str,
        journey_name: Optional[str] = None,
        top_k: int = 5
    ) -> Dict[str, Any]:
        """
        Query the RAG system with a question using native FAISS
        
        Args:
            question: The question to answer
            journey_name: Journey name to search within (required)
            top_k: Number of relevant chunks to retrieve
            
        Returns:
            Dict containing answer and evidence
        """
        try:
            if not journey_name:
                return {
                    "success": False,
                    "answer": "Please specify a journey name to search within.",
                    "evidence": [],
                    "question": question
                }
            
            # Load the FAISS index for the journey
            index = self._load_index(journey_name)
            
            if index is None or index.ntotal == 0:
                return {
                    "success": False,
                    "answer": f"No documents have been indexed for journey '{journey_name}' yet.",
                    "evidence": [],
                    "question": question
                }
            
            metadata = self.loaded_metadata.get(journey_name, [])
            
            if not metadata:
                return {
                    "success": False,
                    "answer": f"No metadata found for journey '{journey_name}'.",
                    "evidence": [],
                    "question": question
                }
            
            logger.info(f"Searching in journey '{journey_name}' with {index.ntotal} vectors")
            
            # Generate query embedding
            query_embedding = self.embedding_model.encode(
                [question],
                convert_to_numpy=True
            ).astype('float32')
            
            # Normalize for cosine similarity
            faiss.normalize_L2(query_embedding)
            
            # Search using FAISS (IndexFlatIP returns cosine similarity scores)
            scores, indices = index.search(query_embedding, min(top_k, index.ntotal))
            
            # Collect results
            evidence = []
            relevant_chunks = []
            
            for score, idx in zip(scores[0], indices[0]):
                if idx < 0 or idx >= len(metadata):
                    continue
                
                doc_metadata = metadata[idx]
                text_content = doc_metadata.get("text", doc_metadata.get("text_preview", ""))
                
                # Convert cosine similarity (0-1) to percentage (0-100)
                # IndexFlatIP returns inner product which is cosine similarity for normalized vectors
                similarity_percentage = float(score) * 100
                similarity_percentage = max(0, min(100, similarity_percentage))
                
                evidence.append({
                    "document": doc_metadata.get("document_filename", "Unknown"),
                    "journey": doc_metadata.get("journey_name", "Unknown"),
                    "chunk_index": doc_metadata.get("chunk_index", 0),
                    "score": round(similarity_percentage, 1),
                    "text": text_content[:500]  # First 500 chars for preview
                })
                
                relevant_chunks.append(text_content)
            
            if not evidence:
                return {
                    "success": False,
                    "answer": "I couldn't find any relevant information to answer your question.",
                    "evidence": [],
                    "question": question
                }
            
            # Build context for LLM (top 5 sources)
            context_blocks = []
            for i, chunk in enumerate(relevant_chunks[:5]):
                source_info = f"[Source {i+1}: {evidence[i]['document']}]"
                context_blocks.append(f"{source_info}\n{chunk}\n")
            
            context = "\n".join(context_blocks)
            
            # Generate answer using LLM with Clinical Assistant style prompt
            system_prompt = """You are a helpful AI assistant that provides accurate information based ONLY on the provided context. You must follow these rules strictly:

1. ONLY use information from the context below to answer the question
2. If the context doesn't contain enough information, explicitly state that
3. Cite sources using the [Source X] format provided in the context
4. Do not use any external knowledge or information not in the context
5. Be precise and clear in your language
6. If you're uncertain, say so clearly
7. Do not use markdown formatting (no **, __, *, etc.)"""

            user_prompt = f"""Context from documents:

{context}

Question: {question}

Answer (cite sources and be concise):"""

            logger.info(f"Generating answer for question: {question[:100]}...")
            logger.info(f"Using {len(evidence)} sources")
            
            response = self.llm.invoke([
                SystemMessage(content=system_prompt),
                HumanMessage(content=user_prompt)
            ])
            
            answer = response.content.strip()
            
            # Clean markdown formatting
            answer = answer.replace("**", "")
            answer = answer.replace("__", "")
            answer = answer.replace("*", "")
            
            logger.info(f"Generated answer: {len(answer)} characters")
            
            return {
                "success": True,
                "answer": answer,
                "evidence": evidence,
                "question": question,
                "sources_count": len(evidence),
                "confidence": "high" if len(evidence) >= 3 else "medium"
            }
            
        except Exception as e:
            logger.error(f"Query failed: {str(e)}", exc_info=True)
            return {
                "success": False,
                "answer": f"Error processing question: {str(e)}",
                "evidence": [],
                "question": question,
                "confidence": "error"
            }
    
    def get_index_stats(self, journey_name: Optional[str] = None) -> Dict[str, Any]:
        """Get statistics about indexed documents"""
        try:
            if journey_name:
                # Get stats for specific journey
                index = self._load_index(journey_name)
                if index is None:
                    return {
                        "success": True,
                        "journey_name": journey_name,
                        "total_vectors": 0,
                        "dimension": self.dimension,
                        "status": "No index found for this journey"
                    }
                
                return {
                    "success": True,
                    "journey_name": journey_name,
                    "total_vectors": index.ntotal,
                    "dimension": self.dimension,
                    "status": "active"
                }
            else:
                # Get stats for all journeys
                all_indexes = []
                if os.path.exists(self.faiss_dir):
                    for item in os.listdir(self.faiss_dir):
                        if item.endswith("_faiss.index"):
                            journey = item.replace("_faiss.index", "")
                            index_path = self._get_index_path(journey)
                            if os.path.exists(index_path):
                                try:
                                    index = faiss.read_index(index_path)
                                    all_indexes.append({
                                        "journey_name": journey,
                                        "total_vectors": index.ntotal
                                    })
                                except Exception as e:
                                    logger.warning(f"Failed to read index for {journey}: {str(e)}")
                                    continue
                
                total_all = sum(idx["total_vectors"] for idx in all_indexes)
                
                return {
                    "success": True,
                    "total_vectors": total_all,
                    "dimension": self.dimension,
                    "journeys": all_indexes,
                    "total_journeys": len(all_indexes)
                }
                
        except Exception as e:
            logger.error(f"Failed to get stats: {str(e)}", exc_info=True)
            return {
                "success": False,
                "error": str(e),
                "total_vectors": 0,
                "dimension": self.dimension
            }


def create_rag_agent():
    """Factory function to create RAG agent"""
    return RAGAgent()
