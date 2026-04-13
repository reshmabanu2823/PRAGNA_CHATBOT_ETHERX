"""Prompt construction utilities."""
from __future__ import annotations

from typing import List, Sequence, Dict, Optional
import logging

import config
from services.memory_management import estimate_tokens

logger = logging.getLogger(__name__)


def build_prompt(
    query: str,
    history: Optional[Sequence[Dict[str, str]]],
    language: str,
    context_text: Optional[str],
    chat_mode: str = "general",
    user_profile_memory: Optional[str] = None,
) -> List[Dict[str, str]]:
    """
    Construct the message list for the final Groq call with token-aware history.
    
    Strategy:
    - Always include current user query
    - Add as much history as possible within token budget
    - Prefer recent messages over older ones
    - Consider context_text size in token calculation
    - Incorporate chat mode for specialized behavior
    
    Args:
        query: Current user query
        history: Conversation history (already pruned by memory_db)
        language: Target language
        context_text: Search context to include
        chat_mode: Chat mode (general, explain_concepts, code_assistance, etc.)
        
    Returns:
        Message list ready for LLM
    """
    # Define mode-specific instructions
    mode_instructions = {
        "general": "You are Pragna, a fast multilingual AI assistant.",
        "explain_concepts": "You are Pragna, an educator specializing in clear explanations. Break down complex concepts into digestible parts. Use examples and analogies.",
        "generate_ideas": "You are Pragna, a creative brainstorming partner. Generate innovative, diverse ideas. Encourage thinking outside the box.",
        "write_content": "You are Pragna, a professional content writer. Create engaging, well-structured, polished content.",
        "code_assistance": "You are Pragna, an expert programmer. Provide clean, efficient, well-commented code with explanations.",
        "ask_questions": "You are Pragna, a thoughtful conversationalist who asks probing questions to deepen understanding.",
        "creative_writing": "You are Pragna, a creative storyteller. Craft vivid narratives, interesting characters, and engaging dialogue.",
    }
    
    base_instruction = mode_instructions.get(chat_mode, "You are Pragna, a fast multilingual AI assistant.")
    language_name = config.SUPPORTED_LANGUAGES.get(language, "English")
    system_parts = [
        base_instruction,
        f"Always respond in {language_name} regardless of the input language.",
        "Be concise for simple questions and thorough for complex ones.",
        (
            "Do not invent model training-cutoff dates, release dates, or internal update details. "
            "If asked about model updates, training data windows, or internal version history, "
            "state you do not have direct visibility and avoid specific dates unless verified context is provided."
        ),
    ]

    if user_profile_memory:
        system_parts.append(
            "Use the following persisted user profile memory to personalize responses without repeatedly asking for the same details. "
            "Treat it as user-provided context, not absolute truth; if it conflicts with the latest message, follow the latest message.\n"
            f"{user_profile_memory}"
        )

    if context_text:
        system_parts.append(
            "Use the following verified context. Weave facts naturally and avoid dumping raw search results.\n"
            f"{context_text}"
        )

    messages: List[Dict[str, str]] = [
        {"role": "system", "content": "\n\n".join(system_parts)}
    ]

    # Calculate available token budget for history
    # Reserve tokens for: query, response buffer, and safety margin
    query_tokens = estimate_tokens(query)
    response_buffer = 500  # Reserve tokens for LLM response
    safety_margin = 200    # Extra buffer to stay safe
    
    system_tokens = estimate_tokens(messages[0]["content"])
    used_tokens = system_tokens + query_tokens + response_buffer + safety_margin
    
    history_budget = max(100, config.MAX_HISTORY_TOKENS - used_tokens)
    
    logger.debug(
        f"📊 Token budget: {history_budget}t for history "
        f"(system: {system_tokens}t, query: {query_tokens}t, buffer: {response_buffer}t)"
    )
    
    # Add history messages that fit in budget, preferring recent messages
    if history:
        current_tokens = 0
        messages_to_include = []
        
        # Work backwards from most recent (important for context)
        for msg in reversed(history):
            msg_tokens = estimate_tokens(msg.get("content", ""))
            
            # Stop if adding this message would exceed budget
            if current_tokens + msg_tokens > history_budget:
                break
            
            messages_to_include.append(msg)
            current_tokens += msg_tokens
        
        # Reverse back to chronological order
        messages_to_include.reverse()
        messages.extend(messages_to_include)
        
        included_count = len(messages_to_include)
        logger.debug(
            f"📝 Included {included_count} history messages ({current_tokens}t) "
            f"out of {len(history)} available"
        )
    
    # Add current query
    messages.append({"role": "user", "content": query})
    return messages
