"""Test Database persona CRUD methods directly (no Flask needed)."""
from database import db


def _cleanup_test_users():
    conn = db.get_connection()
    try:
        cur = conn.cursor()
        param = '?' if db.is_sqlite else '%s'
        cur.execute(f"DELETE FROM personas WHERE user_id LIKE {param}", ("test-user-personas%",))
        cur.execute(f"DELETE FROM users WHERE id LIKE {param} OR username LIKE {param}", ("test-user-personas%", "test-user-personas%"))
        conn.commit()
    finally:
        db.release_connection(conn)


def _ensure_user(user_id):
    conn = db.get_connection()
    try:
        cur = conn.cursor()
        param = '?' if db.is_sqlite else '%s'
        if db.is_sqlite:
            cur.execute(
                f"INSERT INTO users (id, username, email, password_hash) VALUES ({param}, {param}, {param}, {param}) ON CONFLICT DO NOTHING",
                (user_id, user_id, f"{user_id}@test.com", "hash_123")
            )
        else:
            cur.execute(
                f"INSERT INTO users (id, username, email, password_hash) VALUES ({param}, {param}, {param}, {param}) ON CONFLICT (id) DO NOTHING",
                (user_id, user_id, f"{user_id}@test.com", "hash_123")
            )
        conn.commit()
    finally:
        db.release_connection(conn)


def test_create_and_list_persona():
    user_id = "test-user-personas-1"
    _ensure_user(user_id)
    persona_id = db.create_persona(user_id, "Concise Coder", "Respond with terse, code-first answers.")
    assert persona_id, "create_persona should return a non-empty id"

    personas = db.list_personas(user_id)
    assert any(p["id"] == persona_id for p in personas), personas
    created = next(p for p in personas if p["id"] == persona_id)
    assert created["name"] == "Concise Coder"
    assert created["system_prompt"] == "Respond with terse, code-first answers."
    print("PASS: create and list persona")


def test_update_persona():
    user_id = "test-user-personas-2"
    _ensure_user(user_id)
    persona_id = db.create_persona(user_id, "Original Name", "Original prompt")
    updated = db.update_persona(persona_id, user_id, "New Name", "New prompt")
    assert updated is True

    persona = db.get_persona(persona_id, user_id)
    assert persona["name"] == "New Name"
    assert persona["system_prompt"] == "New prompt"
    print("PASS: update persona")


def test_update_persona_wrong_owner_fails():
    owner_id = "test-user-personas-3"
    other_id = "test-user-personas-4"
    _ensure_user(owner_id)
    _ensure_user(other_id)
    persona_id = db.create_persona(owner_id, "Owned Persona", "prompt")

    result = db.update_persona(persona_id, other_id, "Hacked Name", "Hacked prompt")
    assert result is False, "update_persona must return False for another user's persona"

    persona = db.get_persona(persona_id, owner_id)
    assert persona["name"] == "Owned Persona", "persona must be unchanged after a rejected cross-user update"
    print("PASS: update_persona rejects wrong owner")


def test_delete_persona():
    user_id = "test-user-personas-5"
    _ensure_user(user_id)
    persona_id = db.create_persona(user_id, "To Delete", "prompt")
    deleted = db.delete_persona(persona_id, user_id)
    assert deleted is True

    persona = db.get_persona(persona_id, user_id)
    assert persona is None
    print("PASS: delete persona")


def test_delete_persona_wrong_owner_fails():
    owner_id = "test-user-personas-6"
    other_id = "test-user-personas-7"
    _ensure_user(owner_id)
    _ensure_user(other_id)
    persona_id = db.create_persona(owner_id, "Protected Persona", "prompt")

    result = db.delete_persona(persona_id, other_id)
    assert result is False, "delete_persona must return False for another user's persona"

    persona = db.get_persona(persona_id, owner_id)
    assert persona is not None, "persona must still exist after a rejected cross-user delete"
    print("PASS: delete_persona rejects wrong owner")


if __name__ == "__main__":
    db.init_db()
    _cleanup_test_users()
    test_create_and_list_persona()
    test_update_persona()
    test_update_persona_wrong_owner_fails()
    test_delete_persona()
    test_delete_persona_wrong_owner_fails()
    print("All persona DB tests passed.")
