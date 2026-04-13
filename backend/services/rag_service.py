"""Retrieval-Augmented Generation (RAG) Service.

Provides document retrieval and context augmentation for improved response accuracy.
Uses sentence-transformers for embeddings and FAISS for efficient vector search.
"""
import logging
import os
import pickle
from typing import List, Dict, Tuple, Optional
import numpy as np

try:
    from sentence_transformers import SentenceTransformer
    import faiss
    HAS_RAG_DEPS = True
except ImportError:
    HAS_RAG_DEPS = False

import config
from services.cache_service import get_cache_service

logger = logging.getLogger(__name__)

# RAG configuration constants
RAG_MODEL_NAME = "all-MiniLM-L6-v2"  # Fast, 384-dim embeddings suitable for on-device
RAG_INDEX_PATH = os.path.join(os.path.dirname(os.path.dirname(__file__)), "temp", "rag_index.faiss")
RAG_METADATA_PATH = os.path.join(os.path.dirname(os.path.dirname(__file__)), "temp", "rag_metadata.pkl")
RAG_CHUNK_SIZE = 300  # Characters per chunk
RAG_CHUNK_OVERLAP = 50  # Overlap between chunks
RAG_TOP_K = 3  # Default number of top results to retrieve
RAG_SIMILARITY_THRESHOLD = 0.5  # Minimum similarity score (0-1)
RAG_CACHE_TTL = 600  # Cache RAG results for 10 minutes


class RAGService:
    """RAG service for document retrieval and context augmentation."""
    
    def __init__(self):
        """Initialize RAG service with sentence transformers and FAISS."""
        self.enabled = HAS_RAG_DEPS
        self.model = None
        self.index = None
        self.metadata = []
        self.cache = get_cache_service()
        self.documents = []
        
        if not self.enabled:
            logger.warning(
                "⚠️ RAG dependencies not installed. "
                "Install: pip install sentence-transformers faiss-cpu"
            )
            return
        
        try:
            logger.info(f"🚀 Loading RAG embedding model: {RAG_MODEL_NAME}")
            self.model = SentenceTransformer(RAG_MODEL_NAME)
            self._load_index()
            logger.info("✅ RAG Service initialized successfully")
        except Exception as e:
            logger.error(f"❌ Failed to initialize RAG service: {e}", exc_info=True)
            self.enabled = False
    
    def _load_index(self):
        """Load FAISS index and metadata from disk if available."""
        try:
            if os.path.exists(RAG_INDEX_PATH) and os.path.exists(RAG_METADATA_PATH):
                self.index = faiss.read_index(RAG_INDEX_PATH)
                with open(RAG_METADATA_PATH, 'rb') as f:
                    self.metadata = pickle.load(f)
                logger.info(f"📚 Loaded RAG index with {len(self.metadata)} documents")
            else:
                logger.debug("No existing RAG index found. Starting with empty index.")
                self.index = None
                self.metadata = []
        except Exception as e:
            logger.error(f"Error loading RAG index: {e}")
            self.index = None
            self.metadata = []
    
    def _save_index(self):
        """Save FAISS index and metadata to disk."""
        try:
            os.makedirs(os.path.dirname(RAG_INDEX_PATH), exist_ok=True)
            if self.index is not None:
                faiss.write_index(self.index, RAG_INDEX_PATH)
                with open(RAG_METADATA_PATH, 'wb') as f:
                    pickle.dump(self.metadata, f)
                logger.debug(f"💾 Saved RAG index ({len(self.metadata)} documents)")
        except Exception as e:
            logger.error(f"Error saving RAG index: {e}")
    
    def _chunk_text(self, text: str, chunk_size: int = RAG_CHUNK_SIZE, 
                    overlap: int = RAG_CHUNK_OVERLAP) -> List[str]:
        """
        Split text into overlapping chunks for better retrieval.
        
        Args:
            text: Text to chunk
            chunk_size: Size of each chunk in characters
            overlap: Overlap between consecutive chunks
            
        Returns:
            List of text chunks
        """
        if not text or len(text) <= chunk_size:
            return [text] if text else []
        
        chunks = []
        start = 0
        
        while start < len(text):
            end = min(start + chunk_size, len(text))
            chunk = text[start:end].strip()
            
            if chunk:
                chunks.append(chunk)

            # Stop when we've reached the end to avoid overlap-based infinite loops.
            if end >= len(text):
                break
            
            # Move start position, accounting for overlap
            start = end - overlap
        
        return chunks
    
    def add_documents(self, documents: List[str], document_ids: List[str] = None) -> bool:
        """
        Add documents to RAG index.
        
        Args:
            documents: List of text documents
            document_ids: Optional list of document identifiers
            
        Returns:
            True if successful
        """
        if not self.enabled or not documents:
            return False
        
        try:
            # Split documents into chunks
            all_chunks = []
            for doc_idx, doc in enumerate(documents):
                chunks = self._chunk_text(doc)
                doc_id = document_ids[doc_idx] if document_ids and doc_idx < len(document_ids) else f"doc_{doc_idx}"
                
                for chunk_idx, chunk in enumerate(chunks):
                    all_chunks.append({
                        'text': chunk,
                        'document_id': doc_id,
                        'chunk_index': chunk_idx
                    })
            
            if not all_chunks:
                logger.warning("No chunks created from documents")
                return False
            
            # Generate embeddings
            chunk_texts = [chunk['text'] for chunk in all_chunks]
            logger.info(f"📊 Generating embeddings for {len(chunk_texts)} chunks...")
            embeddings = self.model.encode(chunk_texts, convert_to_numpy=True)
            
            # Create or update FAISS index
            if embeddings.size > 0:
                embedding_dim = embeddings.shape[1]
                
                if self.index is None:
                    # Create new index
                    self.index = faiss.IndexFlatL2(embedding_dim)
                    logger.info(f"Created new FAISS index (dim={embedding_dim})")
                
                # Add embeddings to index
                self.index.add(embeddings.astype(np.float32))
                self.metadata.extend(all_chunks)
                
                logger.info(f"✅ Added {len(all_chunks)} chunks to RAG index")
                self._save_index()
                return True
            
            return False
        
        except Exception as e:
            logger.error(f"Error adding documents to RAG: {e}", exc_info=True)
            return False
    
    def retrieve_context(self, query: str, top_k: int = RAG_TOP_K, 
                        similarity_threshold: float = RAG_SIMILARITY_THRESHOLD) -> Dict:
        """
        Retrieve relevant context for a query using semantic search.
        
        Args:
            query: User query
            top_k: Number of top results to retrieve
            similarity_threshold: Minimum similarity score (0-1, faiss uses L2 distance)
            
        Returns:
            Dict with 'context' (combined text), 'sources' (list of chunks), 'found' (bool)
        """
        if not self.enabled or self.index is None or not self.metadata:
            logger.debug("RAG not available or no documents indexed")
            return {'context': None, 'sources': [], 'found': False}
        
        try:
            # Check cache first
            cache_key = self.cache.generate_cache_key(query, language="rag", cache_type="rag_retrieval")
            cached_result = self.cache.get_cache(cache_key)
            
            if cached_result is not None:
                logger.debug(f"🔥 RAG cache HIT")
                return cached_result
            
            # Generate query embedding
            query_embedding = self.model.encode([query], convert_to_numpy=True)
            
            # Search FAISS index
            # FAISS L2 distance: lower = more similar
            distances, indices = self.index.search(query_embedding.astype(np.float32), top_k)
            
            # Convert L2 distance to similarity score (0-1, where 1 = identical)
            # L2 distance formula can vary; simple normalization: similarity = 1 / (1 + distance)
            results = []
            for dist, idx in zip(distances[0], indices[0]):
                idx = int(idx)  # Convert numpy int to Python int
                if idx >= 0 and idx < len(self.metadata):
                    # Convert L2 distance to similarity (0-1)
                    similarity = 1.0 / (1.0 + float(dist))
                    
                    if similarity >= similarity_threshold:
                        results.append({
                            'text': self.metadata[idx]['text'],
                            'document_id': self.metadata[idx]['document_id'],
                            'similarity': similarity
                        })
            
            # Combine results into context
            if results:
                context_parts = [r['text'] for r in results]
                combined_context = "\n\n".join(context_parts)
                
                result = {
                    'context': combined_context,
                    'sources': results,
                    'found': True
                }
            else:
                result = {
                    'context': None,
                    'sources': [],
                    'found': False
                }
            
            # Cache the result
            self.cache.set_cache(cache_key, result, RAG_CACHE_TTL)
            
            if results:
                logger.info(f"📚 RAG retrieved {len(results)} relevant chunks (top similarity: {results[0]['similarity']:.2f})")
            else:
                logger.debug(f"📚 RAG: No results above threshold ({similarity_threshold})")
            
            return result
        
        except Exception as e:
            logger.error(f"Error retrieving RAG context: {e}", exc_info=True)
            return {'context': None, 'sources': [], 'found': False}
    
    def clear_index(self) -> bool:
        """Clear all documents from RAG index."""
        try:
            self.index = None
            self.metadata = []
            
            # Remove index files
            for path in [RAG_INDEX_PATH, RAG_METADATA_PATH]:
                if os.path.exists(path):
                    os.remove(path)
            
            logger.info("🧹 RAG index cleared")
            return True
        except Exception as e:
            logger.error(f"Error clearing RAG index: {e}")
            return False
    
    def get_stats(self) -> Dict:
        """Get statistics about the RAG index."""
        return {
            'enabled': self.enabled,
            'has_index': self.index is not None,
            'document_count': len(self.metadata),
            'model': RAG_MODEL_NAME if self.enabled else None
        }


# Global RAG service instance
_rag_service: Optional[RAGService] = None


def get_rag_service() -> RAGService:
    """Get singleton RAG service instance."""
    global _rag_service
    if _rag_service is None:
        _rag_service = RAGService()
    return _rag_service


# Default knowledge base documents (can be expanded or loaded from files)
DEFAULT_DOCUMENTS = [
    """Pragna is a multilingual AI assistant built with Python and React.
    It supports 11 languages including English, Hindi, Tamil, Telugu, Kannada, 
    Malayalam, Marathi, Gujarati, Punjabi, Bengali, and Urdu.
    The backend uses Groq API with Llama models for fast, free LLM inference.""",
    
    """India's geography spans diverse regions from the Himalayas in the north 
    to coastal plains in the south. The country has 28 states and 8 union territories.
    Major cities include Delhi, Mumbai, Bangalore, Chennai, and Kolkata.
    The population exceeds 1.4 billion people.""",
    
    """Python is a versatile programming language used for web development, 
    data science, AI, and automation. Popular frameworks include Flask for web apps,
    Django for full-stack development, and PyTorch/TensorFlow for machine learning.""",
    
    """Machine Learning (ML) is a branch of artificial intelligence that enables 
    systems to learn from data without explicit programming. Key concepts include 
    supervised learning, unsupervised learning, reinforcement learning, and deep learning.""",
    
    """RAG (Retrieval-Augmented Generation) combines information retrieval with 
    generative AI. It retrieves relevant documents first, then uses them to 
    generate more accurate and factual responses. This reduces hallucinations.""",
]


def initialize_rag_with_defaults() -> bool:
    """Initialize RAG service with default knowledge base documents."""
    try:
        rag = get_rag_service()
        if not rag.enabled:
            logger.warning("RAG not enabled; skipping initialization")
            return False
        
        # Only add if index is empty
        if rag.index is None:
            logger.info("🚀 Initializing RAG with default knowledge base...")
            success = rag.add_documents(DEFAULT_DOCUMENTS)
            if success:
                logger.info("✅ RAG initialized with default documents")
                return True
        else:
            logger.info(f"ℹ️ RAG already has {len(rag.metadata)} documents")
            return True
    
    except Exception as e:
        logger.error(f"Error initializing RAG: {e}", exc_info=True)
        return False
