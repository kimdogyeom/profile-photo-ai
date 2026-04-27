import re
from pathlib import Path


def test_makefile_contains_test_and_lint_targets():
    """Root Makefile should expose convenience test/lint targets."""
    content = Path("Makefile").read_text(encoding="utf-8")

    assert re.search(r"(?m)^\.PHONY: .*\btest\b.*\blint\b", content)
    assert re.search(r"(?m)^test:\s*##", content)
    assert re.search(r"(?m)^lint:\s*##", content)
