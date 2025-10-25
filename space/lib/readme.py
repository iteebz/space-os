from pathlib import Path


def load(module_name: str) -> str:
    """Load README.md for a module."""
    here = Path(__file__).parent.parent

    readme = here / module_name / "README.md"
    if readme.exists():
        return readme.read_text()

    core_readme = here / "core" / module_name / "README.md"
    if core_readme.exists():
        return core_readme.read_text()

    apps_readme = here.parent / "apps" / module_name / "README.md"
    if apps_readme.exists():
        return apps_readme.read_text()
    return ""


def root() -> str:
    """Load root README.md."""
    here = Path(__file__).parent.parent.parent
    readme = here / "README.md"
    if readme.exists():
        return readme.read_text()
    return ""
