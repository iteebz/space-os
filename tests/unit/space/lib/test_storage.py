import os
from pathlib import Path

import space.lib.db_utils as db_utils


def test_root_from_subdirectory():
    """Verify that root() finds the project root even when run from a subdirectory."""
    # The true project root is where AGENTS.md exists
    expected_root = Path("/Users/teebz/dev/space")

    # Change to a deep subdirectory
    os.chdir(expected_root / "private" / "agent-space")

    # Call the function to test
    actual_root = db_utils.root()

    # Assert that the function correctly found the project root
    assert actual_root == expected_root
