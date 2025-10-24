"""Command-level aliasing system for unified CLI experience."""

from dataclasses import dataclass


@dataclass
class AliasRule:
    """Defines how to rewrite a command."""

    pattern: list[str]
    rewrite: list[str]


class Aliasing:
    """
    Declarative command aliasing at argv level.
    Rewrites happen before typer parses, enabling:
    - bridge list → bridge channels list
    - wake hailot → wake --as hailot
    - bridge hailot → bridge --as hailot
    """

    RULES = [
        AliasRule(["bridge", "list"], ["bridge", "channels", "list"]),
        AliasRule(["bridge"], ["bridge"]),
        AliasRule(["wake"], ["wake"]),
        AliasRule(["sleep"], ["sleep"]),
    ]

    @staticmethod
    def rewrite(argv: list[str]) -> list[str]:
        """Rewrite argv using alias rules. Processes positional identity args."""
        if not argv:
            return argv

        for rule in Aliasing.RULES:
            if Aliasing._matches(argv, rule.pattern):
                return Aliasing._apply(argv, rule)

        return argv

    @staticmethod
    def get_routes(cmd: str) -> dict[str, bool]:
        """Get available routes for a command."""
        return {rule.rewrite[0]: True for rule in Aliasing.RULES}

    @staticmethod
    def _matches(argv: list[str], pattern: list[str]) -> bool:
        """Check if argv starts with pattern."""
        if len(argv) < len(pattern):
            return False
        return argv[: len(pattern)] == pattern

    @staticmethod
    def _apply(argv: list[str], rule: AliasRule) -> list[str]:
        """Apply alias rule: replace pattern with rewrite, handle identity."""
        rewritten = rule.rewrite.copy()
        remaining = argv[len(rule.pattern) :]

        if remaining and not remaining[0].startswith("-"):
            rewritten.extend(["--as", remaining[0]])
            remaining = remaining[1:]

        rewritten.extend(remaining)
        return rewritten
