from . import paths


def load_canon() -> str | None:
    canon = paths.canon_path()
    if not canon.exists():
        return None
    return canon.read_text().strip()


def inject_canon(constitution: str) -> str:
    """Inject canon at top of constitution if it exists."""
    canon = load_canon()
    if not canon:
        return constitution
    return f"{canon}\n\n{constitution}"


def init_canon() -> None:
    """Create default canon.md if it doesn't exist."""
    canon = paths.canon_path()
    if canon.exists():
        return

    canon.parent.mkdir(parents=True, exist_ok=True)
    canon.write_text("""# CANON

My three core values that guide all agent behavior:

1. [First value - what matters most to you]
2. [Second value - what comes next]
3. [Third value - what completes your foundation]

---
This file injects into every agent constitution.
Edit to align agents with your principles.""")
