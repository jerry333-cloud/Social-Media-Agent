"""Query parsing and preprocessing for RAG."""

import re
from typing import List, Optional
import logging

logger = logging.getLogger(__name__)


class QueryParser:
    """Parses and preprocesses queries for RAG retrieval."""
    
    @staticmethod
    def parse(query: str) -> str:
        """
        Parse and clean query.
        
        Args:
            query: Raw query string
            
        Returns:
            Cleaned query string
        """
        if not query:
            return ""
        
        # Remove extra whitespace
        query = re.sub(r'\s+', ' ', query.strip())
        
        # Remove special characters that might break FTS5
        # Keep alphanumeric, spaces, and common punctuation
        query = re.sub(r'[^\w\s\-.,!?]', ' ', query)
        
        return query.strip()
    
    @staticmethod
    def extract_keywords(query: str, max_keywords: int = 10) -> List[str]:
        """
        Extract key terms from query.
        
        Args:
            query: Query string
            max_keywords: Maximum number of keywords to extract
            
        Returns:
            List of keywords
        """
        # Simple keyword extraction: remove stop words and get meaningful terms
        stop_words = {
            'the', 'a', 'an', 'and', 'or', 'but', 'in', 'on', 'at', 'to', 'for',
            'of', 'with', 'by', 'from', 'as', 'is', 'was', 'are', 'were', 'be',
            'been', 'being', 'have', 'has', 'had', 'do', 'does', 'did', 'will',
            'would', 'should', 'could', 'may', 'might', 'must', 'can', 'this',
            'that', 'these', 'those', 'i', 'you', 'he', 'she', 'it', 'we', 'they'
        }
        
        # Tokenize and filter
        words = re.findall(r'\b\w+\b', query.lower())
        keywords = [w for w in words if w not in stop_words and len(w) > 2]
        
        # Remove duplicates while preserving order
        seen = set()
        unique_keywords = []
        for kw in keywords:
            if kw not in seen:
                seen.add(kw)
                unique_keywords.append(kw)
        
        return unique_keywords[:max_keywords]
    
    @staticmethod
    def validate(query: str) -> bool:
        """
        Validate query quality.
        
        Args:
            query: Query string
            
        Returns:
            True if query is valid, False otherwise
        """
        if not query or not query.strip():
            return False
        
        # Check minimum length
        if len(query.strip()) < 3:
            return False
        
        # Check if query has meaningful content (not just punctuation)
        if not re.search(r'\w', query):
            return False
        
        return True
    
    @staticmethod
    def expand_query(query: str) -> str:
        """
        Expand query with synonyms or related terms (simple implementation).
        
        Args:
            query: Original query
            
        Returns:
            Expanded query
        """
        # Simple expansion: add common variations
        # In production, you might use a synonym dictionary or LLM
        
        expansions = {
            'ai': 'artificial intelligence machine learning',
            'ml': 'machine learning',
            'tech': 'technology',
        }
        
        expanded = query.lower()
        for term, expansion in expansions.items():
            if term in expanded:
                expanded = expanded.replace(term, f"{term} {expansion}")
        
        return expanded
