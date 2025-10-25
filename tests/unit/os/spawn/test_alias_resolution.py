"""Test alias resolution for unified command routing."""

from space.os.lib.aliasing import Aliasing


def test_alias_normalize_positional_identity():
    result = Aliasing.rewrite(["wake", "hailot"])
    assert "--as" in result
    assert "hailot" in result


def test_alias_preserve_existing_flags():
    result = Aliasing.rewrite(["wake", "--as", "hailot"])
    assert result == ["wake", "--as", "hailot"]


def test_alias_preserve_non_identity_args():
    result = Aliasing.rewrite(["memory", "list", "--json"])
    # memory list is a subcommand, not identity alias
    assert result == ["memory", "list", "--json"]


def test_alias_resolve_command_path():
    routes = Aliasing.get_routes("bridge")
    assert "bridge" in routes
    assert "bridge" in routes


def test_alias_supports_direct_shortcuts():
    rewritten = Aliasing.rewrite(["wake", "--as", "hailot"])
    assert "--as" in rewritten
    assert "hailot" in rewritten
