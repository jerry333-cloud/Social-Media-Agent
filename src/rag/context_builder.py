"""Context builder for assembling retrieved chunks into LLM prompts."""

from typing import List, Dict, Optional
import logging

logger = logging.getLogger(__name__)

# Maximum tokens for context (leave room for prompt and response)
# Reduced for Nemotron model's limited context window
# Keep context under 400 tokens (~1600 chars) for safety
MAX_CONTEXT_TOKENS = 400


class ContextBuilder:
    """Builds context from retrieved chunks for LLM consumption."""
    
    def __init__(self, max_tokens: int = MAX_CONTEXT_TOKENS):
        """
        Initialize context builder.
        
        Args:
            max_tokens: Maximum tokens to include in context
        """
        self.max_tokens = max_tokens
    
    def build(
        self,
        chunks: List[Dict],
        include_metadata: bool = True,
        group_by_source: bool = True
    ) -> str:
        """
        Build context string from chunks.
        
        Args:
            chunks: List of chunk dictionaries from retriever
            include_metadata: Whether to include source metadata
            group_by_source: Whether to group chunks by source page
            
        Returns:
            Formatted context string
        """
        if not chunks:
            return ""
        
        # Group by source if requested
        if group_by_source:
            grouped = {}
            for chunk in chunks:
                page_id = chunk.get('page_id', 'unknown')
                if page_id not in grouped:
                    grouped[page_id] = []
                grouped[page_id].append(chunk)
            
            # Sort groups by highest score in group
            sorted_groups = sorted(
                grouped.items(),
                key=lambda x: max(c['final_score'] for c in x[1]),
                reverse=True
            )
        else:
            # Single group with all chunks
            sorted_groups = [('all', chunks)]
        
        # Build context sections
        sections = []
        total_tokens = 0
        
        for page_id, page_chunks in sorted_groups:
            if total_tokens >= self.max_tokens:
                break
            
            # Sort chunks within page by score
            page_chunks.sort(key=lambda x: x.get('chunk_index', 0))
            
            page_section = []
            
            if include_metadata and len(sorted_groups) > 1:
                page_section.append(f"## Source: {page_id}\n")
            
            for chunk in page_chunks:
                chunk_tokens = chunk.get('token_count', 0)
                
                if total_tokens + chunk_tokens > self.max_tokens:
                    # Truncate this chunk if needed
                    remaining_tokens = self.max_tokens - total_tokens
                    if remaining_tokens > 50:  # Only include if meaningful
                        content = chunk['content']
                        # Rough truncation (1 token ≈ 4 chars)
                        max_chars = remaining_tokens * 4
                        if len(content) > max_chars:
                            content = content[:max_chars] + "..."
                        page_section.append(content)
                        total_tokens += remaining_tokens
                    break
                
                page_section.append(chunk['content'])
                total_tokens += chunk_tokens
            
            if page_section:
                sections.append("\n\n".join(page_section))
        
        context = "\n\n---\n\n".join(sections)
        
        logger.debug(f"Built context with {total_tokens} tokens from {len(chunks)} chunks")
        return context
    
    def build_with_scores(
        self,
        chunks: List[Dict],
        show_scores: bool = False
    ) -> str:
        """
        Build context with optional score information.
        
        Args:
            chunks: List of chunk dictionaries
            show_scores: Whether to include relevance scores
            
        Returns:
            Formatted context string with optional scores
        """
        if show_scores:
            # Add score annotations
            annotated_chunks = []
            for chunk in chunks:
                score = chunk.get('final_score', 0.0)
                content = chunk['content']
                annotated = f"[Relevance: {score:.2f}]\n{content}"
                annotated_chunks.append({
                    **chunk,
                    'content': annotated
                })
            return self.build(annotated_chunks, include_metadata=True)
        else:
            return self.build(chunks, include_metadata=True)
