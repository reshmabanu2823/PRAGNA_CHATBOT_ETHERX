#!/usr/bin/env python3
"""
Test script verifying code_agent's file tools stay sandboxed to `root`.
"""
import shutil
import sys
import tempfile
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent))

from services import code_agent


def run_tests():
    workdir = Path(tempfile.mkdtemp(prefix="pragna_sandbox_test_"))
    outside = Path(tempfile.mkdtemp(prefix="pragna_sandbox_outside_"))
    try:
        print("=== Write inside root succeeds ===")
        result = code_agent.tool_write_file(workdir, "inside.txt", "hello")
        print(result)
        assert result.startswith("OK:")
        assert (workdir / "inside.txt").read_text() == "hello"

        print("\n=== Relative escape is rejected ===")
        result = code_agent.tool_write_file(workdir, "../escape.txt", "pwned")
        print(result)
        assert result.startswith("ERROR:")
        assert "outside the allowed working directory" in result
        assert not (workdir.parent / "escape.txt").exists()

        print("\n=== Absolute escape is rejected ===")
        target = outside / "absolute.txt"
        result = code_agent.tool_write_file(workdir, str(target), "pwned")
        print(result)
        assert result.startswith("ERROR:")
        assert not target.exists()

        print("\n=== read_file respects the same sandbox ===")
        result = code_agent.tool_read_file(workdir, "../../etc/passwd")
        print(result)
        assert result.startswith("ERROR:")

        print("\nAll sandbox checks passed.")
    finally:
        shutil.rmtree(workdir, ignore_errors=True)
        shutil.rmtree(outside, ignore_errors=True)


if __name__ == "__main__":
    run_tests()
