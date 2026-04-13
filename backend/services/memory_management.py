"""Memory management and dynamic history optimization.

Provides intelligent conversation history pruning and token-based optimization
to maintain context quality while staying within token limits.
"""
import logging
from typing import List, Dict, Tuple
from datetime import datetime

import config

logger = logging.getLogger(__name__)


def estimate_tokens(text: str) -> int:
    """
    Rough estimate of tokens for Llama models.
    
    Approximation: 1 token ≈ 4 characters (conservative estimate for Llama).
    This is a heuristic; actual token count depends on tokenizer.
    
    Args:
        text: Text to estimate tokens for
        
    Returns:
        Estimated token count
    """
    if not text:
        return 0
    
    # Character count * multiplier
    estimated = int(len(text) * config.TOKEN_ESTIMATE_MULTIPLIER)
    
    # Minimum 1 token per message piece
    return max(1, estimated)


def calculate_message_importance_score(
    message: Dict[str, str],
    index: int,
    total_messages: int
) -> float:
    """
    Calculate importance score for a message for smart pruning.
    
    Scoring considers:
    - Recency: Recent messages get higher scores (exponential decay)
    - Role: User queries are more important than assistant responses
    - Content: Longer, detailed messages score higher
    - Question: Messages with questions are important for context
    
    Args:
        message: Message dict with 'role' and 'content'
        index: Position in history (0 = oldest)
        total_messages: Total number of messages
        
    Returns:
        Importance score (higher = more important)
    """
    if not message or 'content' not in message:
        return 0.0
    
    weights = config.MESSAGE_IMPORTANCE_WEIGHTS
    score = 0.0
    content = message.get('content', '')
    role = message.get('role', 'user')
    
    # 1. Recency boost - exponential (recent messages more important)
    # Messages near end (high index) get higher scores
    recency_ratio = index / max(1, total_messages - 1)  # 0 (oldest) to 1 (newest)
    recency_score = (2 ** recency_ratio) - 1  # Exponential: 0 to 1
    score += recency_score * weights['recent_boost']
    
    # 2. Role-based weight - User queries are more important
    if role == 'user':
        score += weights['user_query_weight']
    else:
        score += weights['assistant_response_weight']
    
    # 3. Content length bonus - Longer messages have more information
    # Normalize by average message length (~100 chars)
    avg_length = 100
    length_ratio = min(1.0, len(content) / avg_length)
    score += length_ratio * weights['long_message_bonus']
    
    # 4. Question bonus - Messages with questions are important for context
    if '?' in content:
        score += weights['question_bonus']
    
    logger.debug(f"Message importance score: {score:.2f} (role: {role}, length: {len(content)}, recency: {recency_ratio:.2f})")
    
    return score


def smart_prune_history(
    messages: List[Dict[str, str]],
    max_tokens: int = None,
    max_messages: int = None,
    min_messages: int = None
) -> Tuple[List[Dict[str, str]], Dict[str, any]]:
    """
    Intelligently prune conversation history while maintaining context quality.
    
    Strategy:
    1. Always keep the minimum recent messages (maintain immediate context)
    2. Score remaining older messages by importance
    3. Keep messages until token budget is exhausted
    4. Prioritize important older messages over trivial recent ones (within reason)
    
    Args:
        messages: Full conversation history (list of dicts with 'role' and 'content')
        max_tokens: Maximum tokens allowed for history (default: config.MAX_HISTORY_TOKENS)
        max_messages: Absolute maximum messages (default: config.MAX_HISTORY_MESSAGES)
        min_messages: Always keep this many recent messages (default: config.MIN_HISTORY_MESSAGES)
        
    Returns:
        Tuple of:
        - Pruned message list
        - Stats dict with pruning information
    """
    # Use config defaults if not specified
    if max_tokens is None:
        max_tokens = config.MAX_HISTORY_TOKENS
    if max_messages is None:
        max_messages = config.MAX_HISTORY_MESSAGES
    if min_messages is None:
        min_messages = config.MIN_HISTORY_MESSAGES
    
    # No pruning needed if history is small
    if len(messages) <= min_messages:
        stats = {
            'total_messages': len(messages),
            'pruned_messages': 0,
            'total_tokens_estimate': sum(estimate_tokens(m.get('content', '')) for m in messages),
            'reason': 'below_minimum_threshold'
        }
        return messages, stats
    
    # Step 1: Enforce absolute message limit
    if len(messages) > max_messages:
        # Keep last max_messages, discard oldest
        messages = messages[-max_messages:]
        logger.info(f"Pruned history to max_messages limit: {max_messages}")
    
    # Step 2: Calculate token count
    total_tokens = sum(estimate_tokens(m.get('content', '')) for m in messages)
    
    # No pruning if under token budget
    if total_tokens <= max_tokens:
        stats = {
            'total_messages': len(messages),
            'pruned_messages': 0,
            'total_tokens_estimate': total_tokens,
            'reason': 'within_token_budget'
        }
        return messages, stats
    
    # Step 3: Must prune to meet token budget
    # Strategy: Keep min recent messages, then add important older messages
    
    logger.info(f"Pruning history: {total_tokens} tokens > {max_tokens} limit")
    
    # Always keep the most recent messages
    recent_messages = messages[-min_messages:]
    older_messages = messages[:-min_messages]
    
    # Score older messages by importance
    scored_messages = []
    for idx, msg in enumerate(older_messages):
        score = calculate_message_importance_score(msg, idx, len(older_messages))
        tokens = estimate_tokens(msg.get('content', ''))
        scored_messages.append({
            'message': msg,
            'score': score,
            'tokens': tokens,
            'index': idx
        })
    
    # Sort by importance score (descending)
    scored_messages.sort(key=lambda x: x['score'], reverse=True)
    
    # Build pruned history by accumulating tokens
    pruned_messages = []
    current_tokens = sum(estimate_tokens(m.get('content', '')) for m in recent_messages)
    
    # Add important older messages until we hit token budget
    for scored in scored_messages:
        msg_tokens = scored['tokens']
        
        # Stop if adding this message would exceed budget
        if current_tokens + msg_tokens > max_tokens:
            continue
        
        pruned_messages.append(scored['message'])
        current_tokens += msg_tokens
    
    # Combine: older important messages + recent messages (maintain chronological order)
    # Sort pruned_messages by original position to maintain order
    pruned_messages_with_index = [(idx, msg) for idx, msg in enumerate(older_messages) 
                                   if msg in pruned_messages]
    pruned_messages_with_index.sort(key=lambda x: x[0])
    sorted_pruned = [msg for _, msg in pruned_messages_with_index]
    
    # Final result: older important + recent
    final_messages = sorted_pruned + recent_messages
    
    pruned_count = len(messages) - len(final_messages)
    
    stats = {
        'total_messages': len(messages),
        'pruned_messages': pruned_count,
        'kept_messages': len(final_messages),
        'original_tokens_estimate': total_tokens,
        'final_tokens_estimate': sum(estimate_tokens(m.get('content', '')) for m in final_messages),
        'token_budget': max_tokens,
        'min_messages_kept': min_messages,
        'reason': 'token_budget_exceeded'
    }
    
    logger.info(f"History pruned: {pruned_count} removed, {len(final_messages)} kept, "
                f"{stats['final_tokens_estimate']} tokens ({stats['original_tokens_estimate']} → {stats['final_tokens_estimate']})")
    
    return final_messages, stats


def get_pruned_history(
    messages: List[Dict[str, str]],
    max_tokens: int = None,
    max_messages: int = None,
    min_messages: int = None
) -> List[Dict[str, str]]:
    """
    Get pruned history (wrapper for convenience).
    
    Args:
        messages: Full conversation history
        max_tokens: Maximum tokens (default: config.MAX_HISTORY_TOKENS)
        max_messages: Absolute maximum messages (default: config.MAX_HISTORY_MESSAGES)
        min_messages: Always keep recent (default: config.MIN_HISTORY_MESSAGES)
        
    Returns:
        Pruned message list ready for LLM
    """
    pruned, _ = smart_prune_history(messages, max_tokens, max_messages, min_messages)
    return pruned
