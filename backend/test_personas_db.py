"""Test Database persona CRUD methods directly (no Flask needed)."""
from database import db


def test_create_and_list_persona():
    user_id = "test-user-personas-1"
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
    persona_id = db.create_persona(owner_id, "Owned Persona", "prompt")

    result = db.update_persona(persona_id, other_id, "Hacked Name", "Hacked prompt")
    assert result is False, "update_persona must return False for another user's persona"

    persona = db.get_persona(persona_id, owner_id)
    assert persona["name"] == "Owned Persona", "persona must be unchanged after a rejected cross-user update"
    print("PASS: update_persona rejects wrong owner")


def test_delete_persona():
    user_id = "test-user-personas-5"
    persona_id = db.create_persona(user_id, "To Delete", "prompt")
    deleted = db.delete_persona(persona_id, user_id)
    assert deleted is True

    persona = db.get_persona(persona_id, user_id)
    assert persona is None
    print("PASS: delete persona")


def test_delete_persona_wrong_owner_fails():
    owner_id = "test-user-personas-6"
    other_id = "test-user-personas-7"
    persona_id = db.create_persona(owner_id, "Protected Persona", "prompt")

    result = db.delete_persona(persona_id, other_id)
    assert result is False, "delete_persona must return False for another user's persona"

    persona = db.get_persona(persona_id, owner_id)
    assert persona is not None, "persona must still exist after a rejected cross-user delete"
    print("PASS: delete_persona rejects wrong owner")


if __name__ == "__main__":
    test_create_and_list_persona()
    test_update_persona()
    test_update_persona_wrong_owner_fails()
    test_delete_persona()
    test_delete_persona_wrong_owner_fails()
    print("All persona DB tests passed.")
