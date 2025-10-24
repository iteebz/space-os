"""Test alias resolution for unified command routing."""

from space.os.lib.aliasing import Aliasing
from space.os.lib.invocation import Invocation


def test_alias_normalize_positional_identity():
    result = Aliasing.normalize_args(["wake", "hailot"])
    assert "--as" in result
    assert "hailot" in result


def test_alias_preserve_existing_flags():
    result = Aliasing.normalize_args(["wake", "--as", "hailot"])
    assert result == ["wake", "--as", "hailot"]


def test_alias_preserve_non_identity_args():
    result = Aliasing.normalize_args(["memory", "list", "--json"])
    # memory list is a subcommand, not identity alias
    assert result == ["memory", "list", "--json"]


def test_alias_resolve_command_path():
    routes = Aliasing.get_routes("bridge")
    assert "bridge" in routes
    assert "bridge" in routes


def test_alias_supports_direct_shortcuts():
    rewritten = Aliasing.rewrite(["wake", "--as", "hailot"])
    ctx = Invocation.from_args(rewritten)
    assert ctx.command == "wake"
    assert ctx.identity == "hailot"
