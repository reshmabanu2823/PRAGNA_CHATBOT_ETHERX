"""
Advanced caching service for Pragna chatbot.

Features:
- In-memory TTL-based caching
- Key normalization and generation
- Cache statistics
- Semantic similarity detection (optional)
"""
import logging
import time
import hashlib
from typing import Any, Dict, Optional, Tuple
from datetime import datetime

logger = logging.getLogger(__name__)


class CacheEntry:
    """Represents a cached value with metadata."""
    
    def __init__(self, value: Any, ttl_seconds: int):
        """
        Initialize cache entry.
        
        Args:
            value: The cached value
            ttl_seconds: Time-to-live in seconds
        """
        self.value = value
        self.ttl_seconds = ttl_seconds
        self.created_at = time.time()
        self.access_count = 0
        self.last_accessed = self.created_at
    
    def is_expired(self) -> bool:
        """Check if the cache entry has expired."""
        elapsed = time.time() - self.created_at
        return elapsed > self.ttl_seconds
    
    def get_value(self) -> Any:
        """Get value and update access metrics."""
        self.access_count += 1
        self.last_accessed = time.time()
        return self.value
    
    def get_age_seconds(self) -> float:
        """Get age of cache entry in seconds."""
        return time.time() - self.created_at
    
    def get_stats(self) -> Dict[str, Any]:
        """Get cache entry statistics."""
        return {
            "age_seconds": self.get_age_seconds(),
            "ttl_seconds": self.ttl_seconds,
            "access_count": self.access_count,
            "last_accessed": datetime.fromtimestamp(self.last_accessed).isoformat(),
            "created_at": datetime.fromtimestamp(self.created_at).isoformat(),
        }


class CacheService:
    """
    In-memory cache with TTL support for Pragna chatbot.
    
    Usage:
        cache = CacheService()
        
        # Set cache
        cache.set_cache("my_query", "cached_response", ttl_seconds=600)
        
        # Get cache
        response = cache.get_cache("my_query")
        
        # Generate cache key
        key = cache.generate_cache_key("What is AI?", "en")
    """
    
    def __init__(self):
        """Initialize the cache service."""
        self._cache: Dict[str, CacheEntry] = {}
        self._stats = {
            "hits": 0,
            "misses": 0,
            "sets": 0,
            "deletes": 0,
            "expirations": 0,
        }
    
    @staticmethod
    def normalize_query(query: str) -> str:
        """
        Normalize query for cache key generation.
        
        Args:
            query: Raw query string
            
        Returns:
            Normalized query (lowercase, stripped, spaces normalized)
        """
        if not query:
            return ""
        
        # Lowercase and strip
        normalized = query.lower().strip()
        
        # Normalize multiple spaces to single space
        normalized = " ".join(normalized.split())
        
        return normalized
    
    @staticmethod
    def generate_cache_key(query: str, language: str = "en", cache_type: str = "llm") -> str:
        """
        Generate a cache key from query and language.
        
        Args:
            query: User query
            language: Language code (en, hi, ta, etc.)
            cache_type: Type of cache (llm, search, news)
            
        Returns:
            Cache key suitable for dictionary lookup
        """
        normalized_query = CacheService.normalize_query(query)
        
        # Create key: type::language::query_hash
        # Using hash to keep key size bounded
        query_hash = hashlib.md5(normalized_query.encode()).hexdigest()[:8]
        cache_key = f"{cache_type}::{language}::{query_hash}::{normalized_query[:50]}"
        
        return cache_key
    
    def get_cache(self, key: str) -> Optional[Any]:
        """
        Retrieve value from cache.
        
        Args:
            key: Cache key
            
        Returns:
            Cached value or None if not found/expired
        """
        if key not in self._cache:
            self._stats["misses"] += 1
            logger.debug(f"Cache MISS: {key}")
            return None
        
        entry = self._cache[key]
        
        # Check if expired
        if entry.is_expired():
            logger.debug(f"Cache EXPIRED: {key} (age: {entry.get_age_seconds():.1f}s)")
            del self._cache[key]
            self._stats["expirations"] += 1
            self._stats["misses"] += 1
            return None
        
        # Cache hit
        value = entry.get_value()
        self._stats["hits"] += 1
        logger.debug(
            f"Cache HIT: {key} (age: {entry.get_age_seconds():.1f}s, "
            f"accesses: {entry.access_count})"
        )
        return value
    
    def set_cache(self, key: str, value: Any, ttl_seconds: int) -> None:
        """
        Store value in cache with TTL.
        
        Args:
            key: Cache key
            value: Value to cache
            ttl_seconds: Time-to-live in seconds
        """
        if not key or value is None:
            logger.warning(f"Skipping cache: invalid key or value")
            return
        
        self._cache[key] = CacheEntry(value, ttl_seconds)
        self._stats["sets"] += 1
        logger.debug(f"Cache SET: {key} (ttl: {ttl_seconds}s)")
    
    def delete_cache(self, key: str) -> bool:
        """
        Delete cache entry.
        
        Args:
            key: Cache key
            
        Returns:
            True if deleted, False if not found
        """
        if key in self._cache:
            del self._cache[key]
            self._stats["deletes"] += 1
            logger.debug(f"Cache DELETE: {key}")
            return True
        
        return False
    
    def clear_cache(self) -> int:
        """
        Clear all cache entries.
        
        Returns:
            Number of entries cleared
        """
        count = len(self._cache)
        self._cache.clear()
        logger.info(f"Cache cleared: {count} entries")
        self._stats["deletes"] += count
        return count
    
    def cleanup_expired(self) -> int:
        """
        Remove all expired entries from cache.
        
        Returns:
            Number of entries removed
        """
        expired_keys = [
            key for key, entry in self._cache.items()
            if entry.is_expired()
        ]
        
        for key in expired_keys:
            del self._cache[key]
            self._stats["expirations"] += 1
        
        if expired_keys:
            logger.info(f"Cleaned up {len(expired_keys)} expired cache entries")
        
        return len(expired_keys)
    
    def get_stats(self) -> Dict[str, Any]:
        """
        Get cache statistics.
        
        Returns:
            Dictionary with cache statistics
        """
        hit_rate = (
            self._stats["hits"] / (self._stats["hits"] + self._stats["misses"])
            if (self._stats["hits"] + self._stats["misses"]) > 0
            else 0
        )
        
        total_entries = len(self._cache)
        approx_memory_bytes = 0
        for key, entry in self._cache.items():
            approx_memory_bytes += len(key.encode("utf-8"))
            try:
                approx_memory_bytes += len(str(entry.value).encode("utf-8"))
            except Exception:
                approx_memory_bytes += 64

        return {
            # Backward-compatible summary fields used by existing endpoints
            "total_hits": self._stats["hits"],
            "total_misses": self._stats["misses"],
            "total_sets": self._stats["sets"],
            "total_entries": total_entries,
            "hit_rate_percent": hit_rate * 100,
            "approx_memory_mb": approx_memory_bytes / (1024 * 1024),
            # Extended stats
            "cache_stats": self._stats,
            "hit_rate": f"{hit_rate * 100:.2f}%",
            "total_operations": sum(self._stats.values()),
            "cache_memory": {
                f"{key[:30]}...": entry.get_stats()
                for key, entry in list(self._cache.items())[:10]  # Show top 10
            },
        }
    
    @staticmethod
    def semantic_similarity(query1: str, query2: str, threshold: float = 0.8) -> bool:
        """
        Simple semantic similarity check using string similarity.
        
        This is a basic implementation. For production, consider:
        - Using embeddings (sentence-transformers)
        - Cosine similarity with TF-IDF
        
        Args:
            query1: First query
            query2: Second query
            threshold: Similarity threshold (0-1)
            
        Returns:
            True if queries are similar enough
        """
        # Normalize both queries
        q1 = CacheService.normalize_query(query1)
        q2 = CacheService.normalize_query(query2)
        
        # Check if they're identical or substrings
        if q1 == q2:
            return True
        
        # Check Levenshtein distance
        if _levenshtein_ratio(q1, q2) >= threshold:
            return True
        
        return False
    
    def find_similar_cache(self, query: str, language: str = "en", 
                          cache_type: str = "llm", threshold: float = 0.85) -> Optional[Tuple[str, Any]]:
        """
        Find cached value for semantically similar query.
        
        Args:
            query: Query to search for
            language: Language code
            cache_type: Type of cache
            threshold: Similarity threshold
            
        Returns:
            Tuple of (cache_key, cached_value) or None
        """
        for key, entry in self._cache.items():
            # Only check same type and language
            if not key.startswith(f"{cache_type}::{language}::"):
                continue
            
            if entry.is_expired():
                continue
            
            # Extract original query from key
            key_parts = key.split("::", 3)
            if len(key_parts) >= 4:
                cached_query = key_parts[3]
                if self.semantic_similarity(query, cached_query, threshold):
                    logger.debug(f"Found similar cache for: {query} -> {cached_query}")
                    return (key, entry.get_value())
        
        return None


def _levenshtein_ratio(s1: str, s2: str) -> float:
    """
    Calculate Levenshtein string similarity ratio (0-1).
    
    Args:
        s1: First string
        s2: Second string
        
    Returns:
        Similarity ratio (1.0 = identical, 0.0 = completely different)
    """
    len1, len2 = len(s1), len(s2)
    
    if max(len1, len2) == 0:
        return 1.0
    
    # Dynamic programming approach
    dp = [[0] * (len2 + 1) for _ in range(len1 + 1)]
    
    for i in range(len1 + 1):
        dp[i][0] = i
    
    for j in range(len2 + 1):
        dp[0][j] = j
    
    for i in range(1, len1 + 1):
        for j in range(1, len2 + 1):
            if s1[i - 1] == s2[j - 1]:
                dp[i][j] = dp[i - 1][j - 1]
            else:
                dp[i][j] = 1 + min(dp[i - 1][j], dp[i][j - 1], dp[i - 1][j - 1])
    
    distance = dp[len1][len2]
    max_len = max(len1, len2)
    
    return 1.0 - (distance / max_len)


# Global cache instance
_cache_instance: Optional[CacheService] = None


def get_cache_service() -> CacheService:
    """
    Get or create the global cache service instance.
    
    Returns:
        CacheService instance
    """
    global _cache_instance
    if _cache_instance is None:
        _cache_instance = CacheService()
        logger.info("✅ Cache service initialized")
    return _cache_instance
