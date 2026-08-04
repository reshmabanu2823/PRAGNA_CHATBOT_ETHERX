"""Test data persistence across simulated server process restarts.

Verifies that users, conversations, messages, and conversation memory (facts/history)
persist reliably in Supabase Postgres (or fallback SQLite) across process / pool re-initializations.
"""
import time
import os
import sys

# Ensure backend folder is in path
sys.path.insert(0, os.path.dirname(__file__))

from database import db
from services import memory_db


def test_cross_restart_persistence():
    print("--- 1. Initializing database schema ---")
    db.init_db()
    memory_db.init_db()

    test_suffix = str(int(time.time()))
    username = f"testuser_{test_suffix}"
    email = f"test_{test_suffix}@example.com"
    user_id = f"uid_{test_suffix}"

    print(f"--- 2. Creating test user ({username}) ---")
    user_created = db._insert_user(username, email, "hashed_password_123", user_id=user_id)
    assert user_created, "Failed to insert user"

    created_conv_id = db.create_conversation(user_created, "Persistent Test Chat", language="en")
    assert created_conv_id, "Failed to create conversation"

    # Add conversation message
    msg_id = db.add_message(created_conv_id, "user", "Hello, testing persistence across restart!")
    assert msg_id, "Failed to add conversation message"

    # Add memory db message and fact
    success, stats = memory_db.add_message(user_created, "user", "My name is PersistenceTester.")
    assert success, "Failed to add memory message 1"

    success2, stats2 = memory_db.add_message(user_created, "user", "I live in San Francisco.")
    assert success2, "Failed to add memory message 2"

    facts_before = memory_db.get_user_profile_facts(user_created)
    assert "name" in facts_before, f"Expected name in facts, got: {facts_before}"
    assert facts_before["name"] == "PersistenceTester"
    assert facts_before.get("location") == "San Francisco"

    print("--- 3. Simulating server restart (resetting pool / connection) ---")
    if hasattr(db, '_pool') and db._pool is not None:
        try:
            db._pool.close()
        except Exception as e:
            print(f"Pool close info: {e}")
        db._pool = None

    # Re-initialize DB
    db.init_db()
    memory_db.init_db()

    print("--- 4. Verifying persistence after simulated restart ---")
    user_after = db.get_user_by_email(email)
    assert user_after is not None, "User lost after restart!"
    assert user_after["username"] == username

    convs_after = db.get_conversations(user_created)
    assert any(c["id"] == created_conv_id for c in convs_after), "Conversation lost after restart!"

    msgs_after = db.get_messages(created_conv_id)
    assert any(m["text"] == "Hello, testing persistence across restart!" for m in msgs_after), "Message lost after restart!"

    memory_msgs_after = memory_db.get_history(user_created, use_smart_pruning=False)
    assert any("PersistenceTester" in m["content"] for m in memory_msgs_after), "Memory history lost after restart!"

    facts_after = memory_db.get_user_profile_facts(user_created)
    assert facts_after.get("name") == "PersistenceTester", f"User fact 'name' lost after restart! Got: {facts_after}"
    assert facts_after.get("location") == "San Francisco", f"User fact 'location' lost after restart! Got: {facts_after}"

    print("PASS: All user, conversation, message, and memory data persisted successfully across restart!")


if __name__ == "__main__":
    test_cross_restart_persistence()
