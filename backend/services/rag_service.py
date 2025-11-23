"""
RAG Service with ChromaDB for persistent vector storage

Provides context-aware conversation using semantic search over historical interactions.
Uses ChromaDB for persistent vector database and sentence-transformers for embeddings.
"""

import structlog
from typing import List, Dict, Optional, Tuple
from datetime import datetime
from pathlib import Path
import hashlib

import chromadb
from chromadb.config import Settings
from sentence_transformers import SentenceTransformer

from storage.conversation_storage import ConversationStorage

logger = structlog.get_logger()


class RAGService:
    """RAG Service with ChromaDB persistent vector storage."""
    
    def __init__(
        self,
        storage: ConversationStorage,
        embedding_model: str = "all-MiniLM-L6-v2",
        persist_directory: str = "./data/vectors"
    ):
        """
        Initialize RAG Service with ChromaDB.
        
        Args:
            storage: ConversationStorage instance for markdown persistence
            embedding_model: SentenceTransformer model name
            persist_directory: Directory for ChromaDB persistent storage
        """
        self.storage = storage
        self.embedding_model_name = embedding_model
        self.persist_directory = Path(persist_directory)
        self.persist_directory.mkdir(parents=True, exist_ok=True)
        
        # Initialize embedding model
        logger.info(f"Loading embedding model: {embedding_model}")
        self.embedding_model = SentenceTransformer(embedding_model)
        
        # Initialize ChromaDB client with persistent storage
        self.chroma_client = chromadb.PersistentClient(
            path=str(self.persist_directory)
        )
        
        # Get or create collection
        self.collection = self.chroma_client.get_or_create_collection(
            name="conversations",
            metadata={"hnsw:space": "cosine"}  # Use cosine similarity
        )
        
        logger.info(
            "RAG Service initialized",
            embedding_model=embedding_model,
            persist_directory=str(self.persist_directory),
            collection_count=self.collection.count()
        )
    
    def _embed_text(self, text: str) -> List[float]:
        """Generate embedding for text."""
        embedding = self.embedding_model.encode(text, convert_to_numpy=True)
        return embedding.tolist()
    
    def _estimate_tokens(self, text: str) -> int:
        """Estimate token count (rough approximation)."""
        return len(text) // 4
    
    async def persist_interaction(
        self,
        session_id: str,
        question: str,
        answer: str,
        metadata: Optional[Dict] = None
    ) -> str:
        """
        Persist interaction to both markdown file and vector store.
        
        Args:
            session_id: Conversation session ID
            question: User question
            answer: AI answer
            metadata: Optional metadata dictionary
            
        Returns:
            Chunk ID for the stored interaction
        """
        # Save to markdown
        await self.storage.save_interaction(
            session_id=session_id,
            question=question,
            answer=answer,
            metadata=metadata or {}
        )
        
        # Create combined text for embedding
        combined_text = f"Q: {question}\nA: {answer}"
        
        # Generate embedding
        embedding = self._embed_text(combined_text)
        
        # Create chunk ID
        timestamp = datetime.utcnow().isoformat()
        chunk_id = f"{session_id}_{timestamp}"
        
        # Prepare metadata for ChromaDB
        chroma_metadata = {
            "session_id": session_id,
            "timestamp": timestamp,
            "question": question[:500],  # Truncate for metadata limits
            "answer": answer[:500]
        }
        
        # Add custom metadata if provided
        if metadata:
            for key, value in metadata.items():
                if isinstance(value, (str, int, float, bool)):
                    chroma_metadata[f"custom_{key}"] = value
        
        # Add to vector store
        self.collection.add(
            ids=[chunk_id],
            embeddings=[embedding],
            documents=[combined_text],
            metadatas=[chroma_metadata]
        )
        
        logger.info(
            "Interaction persisted",
            session_id=session_id,
            chunk_id=chunk_id
        )
        
        return chunk_id
    
    def retrieve_context(
        self,
        query: str,
        session_id: str,
        top_k: int = 5,
        max_tokens: int = 4000,
        recency_weight: float = 0.3
    ) -> List[str]:
        """
        Retrieve relevant context chunks for a query.
        
        Args:
            query: Search query
            session_id: Session to retrieve from
            top_k: Maximum number of chunks to retrieve
            max_tokens: Maximum total tokens to return
            recency_weight: Weight for recency in scoring (0-1)
            
        Returns:
            List of relevant context chunks
        """
        # Generate query embedding
        query_embedding = self._embed_text(query)
        
        # Query vector store with session filter
        results = self.collection.query(
            query_embeddings=[query_embedding],
            n_results=min(top_k * 2, 50),  # Get extra for filtering
            where={"session_id": session_id}
        )
        
        if not results['documents'] or not results['documents'][0]:
            return []
        
        # Extract chunks and metadata
        chunks = results['documents'][0]
        metadatas = results['metadatas'][0]
        distances = results['distances'][0]
        
        # Calculate recency-weighted scores
        scored_chunks = []
        for i, (chunk, metadata, distance) in enumerate(zip(chunks, metadatas, distances)):
            # Parse timestamp
            try:
                timestamp = datetime.fromisoformat(metadata['timestamp'])
                age_seconds = (datetime.utcnow() - timestamp).total_seconds()
                age_hours = age_seconds / 3600
                
                # Recency factor (decays over time)
                recency_factor = 1.0 / (1.0 + age_hours / 24.0)
            except:
                recency_factor = 0.5
            
            # Combine similarity score with recency
            similarity_score = 1.0 - distance  # Convert distance to similarity
            final_score = (
                (1 - recency_weight) * similarity_score +
                recency_weight * recency_factor
            )
            
            scored_chunks.append((chunk, final_score, metadata))
        
        # Sort by final score
        scored_chunks.sort(key=lambda x: x[1], reverse=True)
        
        # Select top chunks within token limit
        selected_chunks = []
        total_tokens = 0
        
        for chunk, score, metadata in scored_chunks[:top_k]:
            chunk_tokens = self._estimate_tokens(chunk)
            if total_tokens + chunk_tokens <= max_tokens:
                selected_chunks.append(chunk)
                total_tokens += chunk_tokens
            else:
                break
        
        # Deduplicate
        selected_chunks = self._deduplicate_chunks(selected_chunks)
        
        logger.info(
            "Context retrieved",
            session_id=session_id,
            query_length=len(query),
            chunks_found=len(selected_chunks),
            total_tokens=total_tokens
        )
        
        return selected_chunks
    
    def _deduplicate_chunks(self, chunks: List[str]) -> List[str]:
        """Remove duplicate or very similar chunks."""
        seen_hashes = set()
        unique_chunks = []
        
        for chunk in chunks:
            # Create hash of chunk
            chunk_hash = hashlib.md5(chunk.encode()).hexdigest()
            
            if chunk_hash not in seen_hashes:
                seen_hashes.add(chunk_hash)
                unique_chunks.append(chunk)
        
        return unique_chunks
    
    def get_collection_stats(self, session_id: Optional[str] = None) -> Dict:
        """
        Get statistics about the vector collection.
        
        Args:
            session_id: Optional session ID to filter stats
            
        Returns:
            Dictionary with collection statistics
        """
        total_count = self.collection.count()
        
        stats = {
            'total_chunks': total_count,
            'embedding_model': self.embedding_model_name,
            'persist_directory': str(self.persist_directory)
        }
        
        if session_id:
            # Count chunks for specific session
            results = self.collection.get(
                where={"session_id": session_id}
            )
            session_count = len(results['ids']) if results['ids'] else 0
            stats['session_id'] = session_id
            stats['session_chunks'] = session_count
        
        return stats
    
    async def update_interaction(
        self,
        session_id: str,
        question: str,
        old_answer: str,
        new_answer: str,
        metadata: Optional[Dict] = None
    ) -> bool:
        """
        Update an existing interaction in the vector store.
        
        Finds and updates the chunk containing the old Q&A pair with the new answer.
        
        Args:
            session_id: Conversation session ID
            question: Original question
            old_answer: Previous answer to be replaced
            new_answer: New answer text
            metadata: Optional metadata dictionary
            
        Returns:
            True if update successful, False if interaction not found
        """
        # Find the chunk to update
        old_combined_text = f"Q: {question}\nA: {old_answer}"
        
        # Query to find the exact chunk
        results = self.collection.get(
            where={"session_id": session_id}
        )
        
        if not results['ids']:
            logger.warning(
                "No chunks found for session",
                session_id=session_id
            )
            return False
        
        # Find matching chunk by comparing documents
        chunk_id_to_update = None
        if results['documents']:
            for i, doc in enumerate(results['documents']):
                # Match by question (more reliable than full text match)
                if question in doc:
                    chunk_id_to_update = results['ids'][i]
                    break
        
        if not chunk_id_to_update:
            logger.warning(
                "Matching chunk not found",
                session_id=session_id,
                question=question[:50]
            )
            return False
        
        # Delete old chunk
        self.collection.delete(ids=[chunk_id_to_update])
        
        # Create new chunk with updated answer
        new_combined_text = f"Q: {question}\nA: {new_answer}"
        embedding = self._embed_text(new_combined_text)
        
        timestamp = datetime.utcnow().isoformat()
        new_chunk_id = f"{session_id}_{timestamp}_edited"
        
        # Prepare metadata
        chroma_metadata = {
            "session_id": session_id,
            "timestamp": timestamp,
            "question": question[:500],
            "answer": new_answer[:500],
            "edited": "true"
        }
        
        if metadata:
            for key, value in metadata.items():
                if isinstance(value, (str, int, float, bool)):
                    chroma_metadata[f"custom_{key}"] = str(value)
        
        # Add updated chunk
        self.collection.add(
            ids=[new_chunk_id],
            embeddings=[embedding],
            documents=[new_combined_text],
            metadatas=[chroma_metadata]
        )
        
        logger.info(
            "Interaction updated",
            session_id=session_id,
            old_chunk_id=chunk_id_to_update,
            new_chunk_id=new_chunk_id
        )
        
        # Also update markdown storage
        # Note: This appends the edit as a new entry - markdown doesn't support in-place edits easily
        await self.storage.save_interaction(
            session_id=session_id,
            question=f"[EDITED] {question}",
            answer=new_answer,
            metadata={"original_answer": old_answer[:100], **(metadata or {})}
        )
        
        return True
    
    def delete_session_chunks(self, session_id: str) -> int:
        """
        Delete all chunks for a session.
        
        Args:
            session_id: Session ID to delete
            
        Returns:
            Number of chunks deleted
        """
        # Get all chunks for session
        results = self.collection.get(
            where={"session_id": session_id}
        )
        
        if not results['ids']:
            return 0
        
        # Delete chunks
        self.collection.delete(
            ids=results['ids']
        )
        
        deleted_count = len(results['ids'])
        
        logger.info(
            "Session chunks deleted",
            session_id=session_id,
            count=deleted_count
        )
        
        return deleted_count
    
    def clear_collection(self) -> None:
        """Clear all data from the collection."""
        # Delete collection
        self.chroma_client.delete_collection("conversations")
        
        # Recreate collection
        self.collection = self.chroma_client.get_or_create_collection(
            name="conversations",
            metadata={"hnsw:space": "cosine"}
        )
        
        logger.info("Collection cleared")


# Singleton instance
_rag_service_instance: Optional[RAGService] = None


def get_rag_service(
    storage: Optional[ConversationStorage] = None,
    embedding_model: str = "all-MiniLM-L6-v2",
    persist_directory: str = "./data/vectors"
) -> RAGService:
    """
    Get or create RAG Service singleton.
    
    Args:
        storage: ConversationStorage instance (required for first call)
        embedding_model: Embedding model name
        persist_directory: ChromaDB persistence directory
        
    Returns:
        RAGService instance
    """
    global _rag_service_instance
    
    if _rag_service_instance is None:
        if storage is None:
            raise ValueError("storage required for first RAGService initialization")
        
        _rag_service_instance = RAGService(
            storage=storage,
            embedding_model=embedding_model,
            persist_directory=persist_directory
        )
    
    return _rag_service_instance
