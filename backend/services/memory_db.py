"""Simple SQLite-based conversation memory store.

Stores conversation history per user in a local SQLite database.
Supports intelligent pruning using token-based optimization and message importance scoring.
"""
import os
import sqlite3
import logging
import re
from contextlib import contextmanager
from typing import List, Dict, Tuple

import config
from services.memory_management import smart_prune_history, estimate_tokens

logger = logging.getLogger(__name__)

# Database file under backend/temp
BASE_DIR = os.path.dirname(os.path.dirname(__file__))
TEMP_DIR = os.path.join(BASE_DIR, "temp")
os.makedirs(TEMP_DIR, exist_ok=True)
DB_PATH = os.path.join(TEMP_DIR, "conversation_memory.db")


@contextmanager
def _get_conn():
    conn = sqlite3.connect(DB_PATH)
    try:
        yield conn
    finally:
        conn.close()


def init_db() -> None:
    """Create tables if they do not exist."""
    with _get_conn() as conn:
        cur = conn.cursor()
        cur.execute(
            """
            CREATE TABLE IF NOT EXISTS messages (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                user_id TEXT NOT NULL,
                role TEXT NOT NULL,
                content TEXT NOT NULL,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
            """
        )
        cur.execute("CREATE INDEX IF NOT EXISTS idx_messages_user ON messages(user_id, id)")
        cur.execute(
            """
            CREATE TABLE IF NOT EXISTS user_facts (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                user_id TEXT NOT NULL,
                fact_key TEXT NOT NULL,
                fact_value TEXT NOT NULL,
                updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                UNIQUE(user_id, fact_key)
            )
            """
        )
        cur.execute("CREATE INDEX IF NOT EXISTS idx_user_facts_user ON user_facts(user_id)")
        conn.commit()


def _clean_fact_value(value: str, max_len: int = 200) -> str:
    if not value:
        return ""
    cleaned = re.sub(r"\s+", " ", value).strip(" .,!?:;\"'")
    return cleaned[:max_len].strip()


def _extract_user_facts(message: str) -> Dict[str, str]:
    """Extract stable personal facts from user messages using lightweight rules."""
    text = (message or "").strip()
    if not text:
        return {}

    text_l = text.lower()
    facts: Dict[str, str] = {}

    name_patterns = [
        r"\bmy name is\s+([A-Za-z][A-Za-z .'-]{1,60})",
        r"\bi am\s+([A-Za-z][A-Za-z .'-]{1,60})\b",
        r"\bi'm\s+([A-Za-z][A-Za-z .'-]{1,60})\b",
    ]
    for pattern in name_patterns:
        m = re.search(pattern, text, re.IGNORECASE)
        if m:
            candidate = _clean_fact_value(m.group(1), 80)
            if candidate and len(candidate.split()) <= 4:
                facts["name"] = candidate
            break

    location_patterns = [
        r"\bi live in\s+([A-Za-z][A-Za-z ,.'-]{1,80})",
        r"\bi am from\s+([A-Za-z][A-Za-z ,.'-]{1,80})",
        r"\bbased in\s+([A-Za-z][A-Za-z ,.'-]{1,80})",
    ]
    for pattern in location_patterns:
        m = re.search(pattern, text, re.IGNORECASE)
        if m:
            facts["location"] = _clean_fact_value(m.group(1), 100)
            break

    profession_patterns = [
        r"\bi work as\s+([A-Za-z][A-Za-z /&,'-]{1,80})",
        r"\bi am a\s+([A-Za-z][A-Za-z /&,'-]{1,80})",
    ]
    for pattern in profession_patterns:
        m = re.search(pattern, text, re.IGNORECASE)
        if m:
            profession = _clean_fact_value(m.group(1), 100)
            if profession and not profession.lower().startswith("little"):
                facts["profession"] = profession
            break

    language_patterns = [
        r"\bi prefer\s+([A-Za-z]+)\s+language",
        r"\brespond in\s+([A-Za-z]+)",
        r"\bi speak\s+([A-Za-z ,/]+)",
    ]
    for pattern in language_patterns:
        m = re.search(pattern, text, re.IGNORECASE)
        if m:
            facts["language_pref"] = _clean_fact_value(m.group(1), 100)
            break

    like_patterns = [
        r"\bi like\s+(.+)",
        r"\bi love\s+(.+)",
        r"\bi prefer\s+(.+)",
    ]
    for pattern in like_patterns:
        m = re.search(pattern, text, re.IGNORECASE)
        if m:
            candidate = _clean_fact_value(m.group(1), 140)
            if candidate and len(candidate.split()) <= 16:
                facts["preference"] = candidate
            break

    if any(k in text_l for k in ["every day", "daily", "usually", "my routine", "i need every day"]):
        routine = _clean_fact_value(text, 180)
        if routine:
            facts["daily_needs"] = routine

    if any(k in text_l for k in ["my goal", "i want to", "i need to", "target is"]):
        goal = _clean_fact_value(text, 180)
        if goal:
            facts["goal"] = goal

    return {k: v for k, v in facts.items() if v}


def _upsert_user_fact(user_id: str, fact_key: str, fact_value: str) -> None:
    if not fact_value:
        return
    with _get_conn() as conn:
        cur = conn.cursor()
        cur.execute(
            """
            INSERT INTO user_facts (user_id, fact_key, fact_value, updated_at)
            VALUES (?, ?, ?, CURRENT_TIMESTAMP)
            ON CONFLICT(user_id, fact_key)
            DO UPDATE SET
                fact_value = excluded.fact_value,
                updated_at = CURRENT_TIMESTAMP
            """,
            (user_id, fact_key, fact_value),
        )
        conn.commit()


def update_user_profile_from_message(user_id: str, message: str) -> Dict[str, str]:
    """Extract and persist user profile facts from a user message."""
    init_db()
    facts = _extract_user_facts(message)
    for key, value in facts.items():
        _upsert_user_fact(user_id, key, value)
    return facts


def get_user_profile_facts(user_id: str) -> Dict[str, str]:
    """Fetch persisted user profile facts as key-value pairs."""
    init_db()
    with _get_conn() as conn:
        cur = conn.cursor()
        cur.execute(
            "SELECT fact_key, fact_value FROM user_facts WHERE user_id = ? ORDER BY updated_at DESC",
            (user_id,),
        )
        rows = cur.fetchall()
    return {key: value for key, value in rows}


def get_user_profile_summary(user_id: str) -> str:
    """Build compact profile summary to inject into system prompt."""
    facts = get_user_profile_facts(user_id)
    if not facts:
        return ""

    labels = {
        "name": "Name",
        "location": "Location",
        "profession": "Profession",
        "language_pref": "Language preference",
        "preference": "Preferences",
        "daily_needs": "Daily needs/routine",
        "goal": "Current goal",
    }
    ordered_keys = [
        "name",
        "location",
        "profession",
        "language_pref",
        "preference",
        "daily_needs",
        "goal",
    ]
    lines = []
    for key in ordered_keys:
        value = facts.get(key)
        if value:
            lines.append(f"- {labels.get(key, key)}: {value}")
    return "\n".join(lines)


def get_history(user_id: str, max_messages: int = None, use_smart_pruning: bool = True) -> List[Dict[str, str]]:
    """
    Return conversation history for a user.
    
    Args:
        user_id: User identifier
        max_messages: Maximum messages to retrieve from DB (for backward compatibility).
                     If None, uses config.CONVERSATION_HISTORY_SIZE
        use_smart_pruning: If True, apply intelligent pruning to optimize context quality
                          
    Returns:
        List of {"role", "content"} dicts ordered by time, optionally pruned
    """
    init_db()
    
    # Use config default if not specified
    if max_messages is None:
        max_messages = config.CONVERSATION_HISTORY_SIZE
    
    # Retrieve all messages (or up to limit) from database
    limit = max_messages * 2 if max_messages and max_messages > 0 else 0
    query = "SELECT role, content FROM messages WHERE user_id=? ORDER BY id ASC"
    params = [user_id]
    if limit:
        query += " LIMIT ?"
        params.append(limit)
    
    with _get_conn() as conn:
        cur = conn.cursor()
        cur.execute(query, params)
        rows = cur.fetchall()
    
    messages = [{"role": r[0], "content": r[1]} for r in rows]
    
    # Apply smart pruning if enabled and history exists
    if use_smart_pruning and messages:
        pruned_messages, stats = smart_prune_history(
            messages,
            max_tokens=config.MAX_HISTORY_TOKENS,
            max_messages=config.MAX_HISTORY_MESSAGES,
            min_messages=config.MIN_HISTORY_MESSAGES
        )
        
        # Log pruning statistics
        if stats['pruned_messages'] > 0:
            logger.info(
                f"📊 History pruned: {stats['pruned_messages']} removed, "
                f"{stats['kept_messages']} kept for user {user_id} | "
                f"Tokens: {stats['final_tokens_estimate']}/{stats['token_budget']}"
            )
        
        return pruned_messages
    
    return messages


def add_message(user_id: str, role: str, content: str, max_messages: int = None) -> Tuple[bool, Dict]:
    """
    Add a message and intelligently prune old history beyond limits.
    
    Uses smart pruning: scores messages by importance and maintains context quality
    while staying within token and message limits.
    
    Args:
        user_id: User identifier
        role: Message role ("user" or "assistant")
        content: Message content
        max_messages: Maximum messages to keep. If None, uses config.CONVERSATION_HISTORY_SIZE
        
    Returns:
        Tuple of (success: bool, stats: dict with pruning info)
    """
    init_db()

    if role == "user" and content:
        try:
            extracted = update_user_profile_from_message(user_id, content)
            if extracted:
                logger.info(f"🧠 Updated user profile memory for {user_id}: {list(extracted.keys())}")
        except Exception as exc:
            logger.warning(f"Failed to update user profile memory for {user_id}: {exc}")
    
    # Use config defaults if not specified
    if max_messages is None:
        max_messages = config.CONVERSATION_HISTORY_SIZE
    
    with _get_conn() as conn:
        cur = conn.cursor()
        
        # Insert new message
        cur.execute(
            "INSERT INTO messages (user_id, role, content) VALUES (?, ?, ?)",
            (user_id, role, content),
        )
        
        # Get all messages for this user to perform smart pruning
        cur.execute(
            "SELECT id, role, content FROM messages WHERE user_id = ? ORDER BY id ASC",
            (user_id,)
        )
        all_rows = cur.fetchall()
        
        # If we have too many messages, apply smart pruning
        messages_list = [{"role": r[1], "content": r[2]} for r in all_rows]
        
        if len(messages_list) > config.MAX_HISTORY_MESSAGES:
            # Apply smart pruning
            pruned_messages, stats = smart_prune_history(
                messages_list,
                max_tokens=config.MAX_HISTORY_TOKENS,
                max_messages=config.MAX_HISTORY_MESSAGES,
                min_messages=config.MIN_HISTORY_MESSAGES
            )
            
            # Build set of IDs to keep (by matching content)
            # This is a bit inefficient but necessary since we don't store importance scores
            ids_to_keep = set()
            msg_content_to_keep = {msg['content'] for msg in pruned_messages}
            
            for row_id, role, content in all_rows:
                if content in msg_content_to_keep:
                    ids_to_keep.add(row_id)
            
            # Delete messages not in the pruned set
            if ids_to_keep:
                placeholders = ','.join('?' * len(ids_to_keep))
                cur.execute(
                    f"DELETE FROM messages WHERE user_id = ? AND id NOT IN ({placeholders})",
                    [user_id] + list(ids_to_keep)
                )
            
            logger.info(
                f"💾 Added message and pruned history: {stats['pruned_messages']} removed | "
                f"Tokens: {stats['final_tokens_estimate']}/{stats['token_budget']}"
            )
            conn.commit()
            return True, stats
        
        # Simple case: just keep last max_messages*2 if no smart pruning needed
        elif max_messages and max_messages > 0:
            cur.execute(
                """
                DELETE FROM messages
                WHERE user_id = ? AND id NOT IN (
                    SELECT id FROM messages
                    WHERE user_id = ?
                    ORDER BY id DESC
                    LIMIT ?
                )
                """,
                (user_id, user_id, max_messages * 2),
            )
            logger.debug(f"💾 Added message (simple retention: max {max_messages * 2})")
        
        conn.commit()
        return True, {"reason": "no_pruning_needed"}



def clear_history(user_id: str) -> None:
    """Delete all messages for a user."""
    init_db()
    with _get_conn() as conn:
        cur = conn.cursor()
        cur.execute("DELETE FROM messages WHERE user_id=?", (user_id,))
        conn.commit()
