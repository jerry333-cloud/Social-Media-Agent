"""Text chunking service for RAG."""

import os
import tiktoken
from typing import List, Dict, Optional
import logging

logger = logging.getLogger(__name__)

# Default chunk size and overlap
DEFAULT_CHUNK_SIZE = int(os.getenv("RAG_CHUNK_SIZE", "300"))
DEFAULT_CHUNK_OVERLAP = int(os.getenv("RAG_CHUNK_OVERLAP", "50"))


class Chunker:
    """Handles text chunking for RAG."""
    
    def __init__(self, chunk_size: int = None, chunk_overlap: int = None):
        """
        Initialize chunker.
        
        Args:
            chunk_size: Target tokens per chunk (default: 300)
            chunk_overlap: Overlap tokens between chunks (default: 50)
        """
        self.chunk_size = chunk_size or DEFAULT_CHUNK_SIZE
        self.chunk_overlap = chunk_overlap or DEFAULT_CHUNK_OVERLAP
        
        # Initialize tiktoken encoder
        try:
            # Use cl100k_base (GPT-4 tokenizer) for accurate token counting
            self.encoder = tiktoken.get_encoding("cl100k_base")
        except Exception as e:
            logger.warning(f"Could not load tiktoken encoder: {e}")
            self.encoder = None
    
    def count_tokens(self, text: str) -> int:
        """
        Count tokens in text.
        
        Args:
            text: Text to count tokens for
            
        Returns:
            Number of tokens
        """
        if self.encoder is None:
            # Fallback: approximate 1 token = 4 characters
            return len(text) // 4
        
        return len(self.encoder.encode(text))
    
    def chunk_text(
        self,
        text: str,
        page_id: str = "",
        metadata: Optional[Dict] = None
    ) -> List[Dict]:
        """
        Chunk text into smaller pieces.
        
        Args:
            text: Text to chunk
            page_id: Source page ID for metadata
            metadata: Additional metadata to include
            
        Returns:
            List of chunk dictionaries with:
            - content: chunk text
            - token_count: number of tokens
            - chunk_index: position in original text
            - page_id: source page ID
            - metadata: additional metadata
        """
        if not text.strip():
            return []
        
        # Split into paragraphs first (respect natural boundaries)
        paragraphs = self._split_into_paragraphs(text)
        
        chunks = []
        current_chunk = []
        current_tokens = 0
        chunk_index = 0
        
        for paragraph in paragraphs:
            para_tokens = self.count_tokens(paragraph)
            
            # If paragraph itself is too large, split it
            if para_tokens > self.chunk_size:
                # Split large paragraph into sentences
                sentences = self._split_into_sentences(paragraph)
                for sentence in sentences:
                    sent_tokens = self.count_tokens(sentence)
                    
                    if current_tokens + sent_tokens > self.chunk_size and current_chunk:
                        # Save current chunk
                        chunk_content = " ".join(current_chunk)
                        chunks.append({
                            "content": chunk_content,
                            "token_count": current_tokens,
                            "chunk_index": chunk_index,
                            "page_id": page_id,
                            "metadata": metadata or {}
                        })
                        chunk_index += 1
                        
                        # Start new chunk with overlap
                        if self.chunk_overlap > 0 and current_chunk:
                            # Take last N tokens for overlap
                            overlap_text = " ".join(current_chunk[-self._get_overlap_sentences(current_chunk):])
                            current_chunk = [overlap_text] if overlap_text else []
                            current_tokens = self.count_tokens(overlap_text)
                        else:
                            current_chunk = []
                            current_tokens = 0
                    
                    current_chunk.append(sentence)
                    current_tokens += sent_tokens
            else:
                # Check if adding paragraph would exceed chunk size
                if current_tokens + para_tokens > self.chunk_size and current_chunk:
                    # Save current chunk
                    chunk_content = " ".join(current_chunk)
                    chunks.append({
                        "content": chunk_content,
                        "token_count": current_tokens,
                        "chunk_index": chunk_index,
                        "page_id": page_id,
                        "metadata": metadata or {}
                    })
                    chunk_index += 1
                    
                    # Start new chunk with overlap
                    if self.chunk_overlap > 0 and current_chunk:
                        overlap_text = " ".join(current_chunk[-self._get_overlap_sentences(current_chunk):])
                        current_chunk = [overlap_text] if overlap_text else []
                        current_tokens = self.count_tokens(overlap_text)
                    else:
                        current_chunk = []
                        current_tokens = 0
                
                current_chunk.append(paragraph)
                current_tokens += para_tokens
        
        # Add final chunk if any remaining
        if current_chunk:
            chunk_content = " ".join(current_chunk)
            chunks.append({
                "content": chunk_content,
                "token_count": current_tokens,
                "chunk_index": chunk_index,
                "page_id": page_id,
                "metadata": metadata or {}
            })
        
        logger.info(f"Chunked text into {len(chunks)} chunks (target: ~{self.chunk_size} tokens each)")
        return chunks
    
    def _split_into_paragraphs(self, text: str) -> List[str]:
        """Split text into paragraphs."""
        # Split by double newlines or single newline if followed by capital letter
        paragraphs = []
        current = []
        
        lines = text.split('\n')
        for line in lines:
            line = line.strip()
            if not line:
                if current:
                    paragraphs.append(' '.join(current))
                    current = []
            else:
                current.append(line)
        
        if current:
            paragraphs.append(' '.join(current))
        
        return paragraphs if paragraphs else [text]
    
    def _split_into_sentences(self, text: str) -> List[str]:
        """Split text into sentences."""
        import re
        # Simple sentence splitting on . ! ? followed by space and capital letter
        sentences = re.split(r'([.!?]\s+[A-Z])', text)
        
        result = []
        for i in range(0, len(sentences), 2):
            if i < len(sentences):
                sentence = sentences[i]
                if i + 1 < len(sentences):
                    sentence += sentences[i + 1]
                if sentence.strip():
                    result.append(sentence.strip())
        
        return result if result else [text]
    
    def _get_overlap_sentences(self, chunk: List[str]) -> int:
        """Calculate how many sentences to include in overlap."""
        # Rough estimate: try to get ~50 tokens worth
        overlap_text = ""
        for sentence in reversed(chunk):
            test_text = sentence + " " + overlap_text
            if self.count_tokens(test_text) <= self.chunk_overlap:
                overlap_text = test_text
            else:
                break
        return len(overlap_text.split('.')) if overlap_text else 1
