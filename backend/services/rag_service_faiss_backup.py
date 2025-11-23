"""
RAG (Retrieval-Augmented Generation) Service

Manages conversation memory using vector embeddings and similarity search.
Enables context-aware question generation by retrieving relevant past interactions.
"""

from typing import List, Dict, Tuple, Optional
from datetime import datetime
import numpy as np
from sentence_transformers import SentenceTransformer
import faiss
import structlog

from storage.conversation_storage import ConversationStorage

logger = structlog.get_logger()


class RAGService:
    """
    Retrieval-Augmented Generation service for conversation context.
    
    Features:
    - Text embedding using sentence-transformers
    - FAISS vector store for efficient similarity search
    - Context window management (4000 tokens)
    - Recency-weighted retrieval
    - Chunk deduplication
    """
    
    def __init__(
        self,
        storage: ConversationStorage,
        model_name: str = 'sentence-transformers/all-MiniLM-L6-v2',
        cache_ttl_seconds: int = 300
    ):
        """
        Initialize RAG service.
        
        Args:
            storage: ConversationStorage instance
            model_name: Sentence transformer model name
            cache_ttl_seconds: Cache TTL for embeddings (default 5 minutes)
        """
        self.storage = storage
        self.model_name = model_name
        self.cache_ttl = cache_ttl_seconds
        
        # Initialize sentence transformer model
        logger.info("loading_sentence_transformer", model=model_name)
        self.model = SentenceTransformer(model_name)
        self.dimension = self.model.get_sentence_embedding_dimension()
        
        # Initialize FAISS index (L2 distance)
        self.index = faiss.IndexFlatL2(self.dimension)
        
        # In-memory storage for chunks and metadata
        self.chunks: List[str] = []
        self.chunk_metadata: List[Dict] = []
        self.session_chunk_map: Dict[str, List[int]] = {}  # session_id -> chunk indices
        
        logger.info(
            "rag_service_initialized",
            model=model_name,
            dimension=self.dimension
        )
    
    def embed_text(self, text: str) -> np.ndarray:
        """
        Generate embedding vector for text.
        
        Args:
            text: Input text to embed
            
        Returns:
            Normalized embedding vector
        """
        try:
            embedding = self.model.encode([text])[0]
            # Normalize for cosine similarity via L2 distance
            norm = np.linalg.norm(embedding)
            if norm > 0:
                embedding = embedding / norm
            return embedding
        except Exception as e:
            logger.error("embed_text_failed", error=str(e))
            raise
    
    async def persist_interaction(
        self,
        session_id: str,
        question: str,
        answer: str,
        metadata: Optional[Dict] = None
    ) -> int:
        """
        Save interaction to storage and add to vector index.
        
        Args:
            session_id: Unique session identifier
            question: Question text
            answer: User's answer
            metadata: Optional metadata (category, etc.)
            
        Returns:
            Index of the added chunk
        """
        # Save to markdown storage
        await self.storage.save_interaction(
            session_id,
            question,
            answer,
            metadata
        )
        
        # Create chunk text for embedding
        chunk_text = f"Q: {question}\nA: {answer}"
        
        # Generate embedding
        embedding = self.embed_text(chunk_text)
        
        # Add to FAISS index
        self.index.add(np.array([embedding], dtype=np.float32))
        
        # Store chunk and metadata
        chunk_idx = len(self.chunks)
        self.chunks.append(chunk_text)
        
        chunk_meta = {
            'session_id': session_id,
            'timestamp': datetime.utcnow(),
            'question': question,
            'answer': answer,
            'category': metadata.get('category', 'unknown') if metadata else 'unknown',
            'chunk_index': chunk_idx
        }
        self.chunk_metadata.append(chunk_meta)
        
        # Update session mapping
        if session_id not in self.session_chunk_map:
            self.session_chunk_map[session_id] = []
        self.session_chunk_map[session_id].append(chunk_idx)
        
        logger.info(
            "interaction_persisted",
            session_id=session_id,
            chunk_index=chunk_idx,
            total_chunks=len(self.chunks)
        )
        
        return chunk_idx
    
    def retrieve_context(
        self,
        query: str,
        session_id: str,
        top_k: int = 5,
        max_tokens: int = 4000
    ) -> List[str]:
        """
        Retrieve relevant context chunks for a query.
        
        Args:
            query: Query text (usually the user's latest answer)
            session_id: Session to retrieve context from
            top_k: Maximum number of chunks to retrieve
            max_tokens: Maximum total tokens in context
            
        Returns:
            List of relevant context chunks
        """
        # Check if session has any chunks
        if session_id not in self.session_chunk_map:
            logger.info("no_context_for_session", session_id=session_id)
            return []
        
        session_chunk_indices = self.session_chunk_map[session_id]
        if not session_chunk_indices:
            return []
        
        try:
            # Embed query
            query_embedding = self.embed_text(query)
            
            # Search in full index
            k = min(top_k * 2, len(self.chunks))  # Get more candidates
            distances, indices = self.index.search(
                np.array([query_embedding], dtype=np.float32),
                k
            )
            
            # Filter to only chunks from this session
            relevant_chunks = []
            total_tokens = 0
            
            for idx in indices[0]:
                if idx >= len(self.chunk_metadata):
                    continue
                
                meta = self.chunk_metadata[idx]
                
                # Only include chunks from this session
                if meta['session_id'] != session_id:
                    continue
                
                chunk = self.chunks[idx]
                
                # Estimate token count (rough: 1 token ≈ 4 chars)
                chunk_tokens = len(chunk) // 4
                
                if total_tokens + chunk_tokens <= max_tokens:
                    relevant_chunks.append({
                        'text': chunk,
                        'metadata': meta,
                        'distance': float(distances[0][list(indices[0]).index(idx)])
                    })
                    total_tokens += chunk_tokens
                
                if len(relevant_chunks) >= top_k:
                    break
            
            # Sort by recency (most recent first) with similarity weighting
            relevant_chunks = self._weight_by_recency_and_similarity(relevant_chunks)
            
            # Deduplicate
            relevant_chunks = self._deduplicate_chunks(relevant_chunks)
            
            # Extract text only
            result = [chunk['text'] for chunk in relevant_chunks[:top_k]]
            
            logger.info(
                "context_retrieved",
                session_id=session_id,
                chunks_retrieved=len(result),
                total_tokens=total_tokens
            )
            
            return result
            
        except Exception as e:
            logger.error("retrieve_context_failed", session_id=session_id, error=str(e))
            return []
    
    def _weight_by_recency_and_similarity(
        self,
        chunks: List[Dict]
    ) -> List[Dict]:
        """
        Sort chunks by recency and similarity score.
        Recent chunks get higher weight.
        
        Args:
            chunks: List of chunk dictionaries with metadata and distance
            
        Returns:
            Sorted list of chunks
        """
        if not chunks:
            return []
        
        # Calculate recency scores (0-1, newer = higher)
        now = datetime.utcnow()
        for chunk in chunks:
            time_diff = (now - chunk['metadata']['timestamp']).total_seconds()
            # Exponential decay: score = e^(-time_diff / 3600)
            # Recent chunks (< 1 hour) get high scores
            recency_score = np.exp(-time_diff / 3600)
            
            # Combine distance (lower is better) with recency
            # Normalize distance to 0-1 range
            similarity_score = 1 / (1 + chunk['distance'])
            
            # Combined score (70% similarity, 30% recency)
            chunk['score'] = 0.7 * similarity_score + 0.3 * recency_score
        
        # Sort by combined score (descending)
        chunks.sort(key=lambda x: x['score'], reverse=True)
        
        return chunks
    
    def _deduplicate_chunks(self, chunks: List[Dict]) -> List[Dict]:
        """
        Remove very similar chunks (likely duplicates).
        
        Args:
            chunks: List of chunk dictionaries
            
        Returns:
            Deduplicated list
        """
        if len(chunks) <= 1:
            return chunks
        
        unique_chunks = []
        seen_hashes = set()
        
        for chunk in chunks:
            # Create a hash from first 100 chars of text
            chunk_hash = hash(chunk['text'][:100])
            
            if chunk_hash not in seen_hashes:
                seen_hashes.add(chunk_hash)
                unique_chunks.append(chunk)
        
        logger.info(
            "chunks_deduplicated",
            original_count=len(chunks),
            unique_count=len(unique_chunks)
        )
        
        return unique_chunks
    
    def get_session_chunk_count(self, session_id: str) -> int:
        """
        Get number of chunks stored for a session.
        
        Args:
            session_id: Session identifier
            
        Returns:
            Number of chunks
        """
        return len(self.session_chunk_map.get(session_id, []))
    
    def clear_session(self, session_id: str) -> int:
        """
        Clear all chunks for a session from memory.
        Note: Does not delete from persistent storage.
        
        Args:
            session_id: Session identifier
            
        Returns:
            Number of chunks cleared
        """
        if session_id not in self.session_chunk_map:
            return 0
        
        chunk_indices = self.session_chunk_map[session_id]
        count = len(chunk_indices)
        
        # Mark chunks as deleted (set to empty)
        for idx in chunk_indices:
            if idx < len(self.chunks):
                self.chunks[idx] = ""
                if idx < len(self.chunk_metadata):
                    self.chunk_metadata[idx]['deleted'] = True
        
        # Remove from session map
        del self.session_chunk_map[session_id]
        
        logger.info("session_cleared", session_id=session_id, chunks_cleared=count)
        
        return count
    
    def get_index_stats(self) -> Dict:
        """
        Get statistics about the vector index.
        
        Returns:
            Dictionary with stats (total_chunks, total_sessions, index_size)
        """
        return {
            'total_chunks': len(self.chunks),
            'total_sessions': len(self.session_chunk_map),
            'index_size': self.index.ntotal,
            'embedding_dimension': self.dimension,
            'model_name': self.model_name
        }


# Dependency injection helper
def get_rag_service(storage: ConversationStorage = None) -> RAGService:
    """
    Get RAGService instance for dependency injection.
    
    Args:
        storage: Optional ConversationStorage instance
        
    Returns:
        RAGService instance
    """
    if storage is None:
        storage = ConversationStorage()
    return RAGService(storage)
