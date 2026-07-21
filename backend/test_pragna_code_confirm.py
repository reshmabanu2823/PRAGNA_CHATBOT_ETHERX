#!/usr/bin/env python3
"""
Test script verifying pragna_code.py's mutating-tool classification and
diff/command preview builder (does not exercise the interactive y/N prompt).
"""
import shutil
import sys
import tempfile
from pathlib import Path
from unittest import mock

ROOT = Path(__file__).parent.parent
sys.path.insert(0, str(ROOT))

import pragna_code


def test_gating_wiring():
    """
    Integration test: verify that _confirm_action gating is wired correctly in run_agent(),
    and that rejection actually blocks dispatch_tool() while approval allows it.
    """
    import os
    workdir = Path(tempfile.mkdtemp(prefix="pragna_cli_gating_test_"))
    cwd = Path.cwd()
    try:
        os.chdir(workdir)

        # Test rejection case: user says "n"
        print("\n=== Integration test: rejection case ===")
        session = pragna_code.Session(str(workdir))

        # Mock _call_ollama to return a write_file tool call on first iteration,
        # and a DONE response on second iteration (which won't happen if rejected)
        ollama_responses = [
            '<tool_call>{"tool": "write_file", "args": {"path": "gated.txt", "content": "hello"}}</tool_call>',
            "DONE: wrote it."
        ]

        with mock.patch.object(pragna_code, "_call_ollama", side_effect=ollama_responses):
            with mock.patch("builtins.input", return_value="n"):
                pragna_code.run_agent(session, "write a file")

        # After rejection, the file should NOT exist
        gated_file = workdir / "gated.txt"
        assert not gated_file.exists(), f"File should not exist after rejection, but {gated_file} exists"
        print(f"✓ File was correctly blocked (does not exist)")

        # Test approval case: user says "y"
        print("\n=== Integration test: approval case ===")
        session = pragna_code.Session(str(workdir))

        # Reset the responses for a fresh run
        ollama_responses = [
            '<tool_call>{"tool": "write_file", "args": {"path": "gated.txt", "content": "hello"}}</tool_call>',
            "DONE: wrote it."
        ]

        with mock.patch.object(pragna_code, "_call_ollama", side_effect=ollama_responses):
            with mock.patch("builtins.input", return_value="y"):
                pragna_code.run_agent(session, "write a file")

        # After approval, the file SHOULD exist with the correct content
        gated_file = workdir / "gated.txt"
        assert gated_file.exists(), f"File should exist after approval, but {gated_file} does not exist"
        content = gated_file.read_text()
        assert content == "hello", f"File content should be 'hello', but got '{content}'"
        print(f"✓ File was correctly created with content: {repr(content)}")

    finally:
        os.chdir(cwd)
        shutil.rmtree(workdir, ignore_errors=True)


def run_tests():
    workdir = Path(tempfile.mkdtemp(prefix="pragna_cli_confirm_test_"))
    cwd = Path.cwd()
    try:
        import os
        os.chdir(workdir)

        print("=== Tool classification ===")
        assert pragna_code.MUTATING_TOOLS == {"write_file", "create_file", "append_file", "run_command"}

        print("\n=== run_command preview ===")
        preview = pragna_code._preview_for("run_command", {"command": "pytest -q"})
        print(preview)
        assert preview == "$ pytest -q"

        print("\n=== write_file preview on a new file ===")
        preview = pragna_code._preview_for("write_file", {"path": "new.txt", "content": "hello\n"})
        print(preview)
        assert "+hello" in preview

        print("\n=== write_file preview on an existing file ===")
        Path("existing.txt").write_text("old\n")
        preview = pragna_code._preview_for("write_file", {"path": "existing.txt", "content": "new\n"})
        print(preview)
        assert "-old" in preview
        assert "+new" in preview

    finally:
        os.chdir(cwd)
        shutil.rmtree(workdir, ignore_errors=True)

    # Run integration test separately
    test_gating_wiring()

    print("\nAll CLI confirm checks passed.")


if __name__ == "__main__":
    run_tests()
