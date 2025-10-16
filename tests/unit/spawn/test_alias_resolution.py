"""Test alias resolution for unified command routing."""

from space.lib.invocation import AliasResolver


def test_alias_normalize_positional_identity():
    result = AliasResolver.normalize_args(["wake", "hailot"])
    assert "--as" in result
    assert "hailot" in result


def test_alias_preserve_existing_flags():
    result = AliasResolver.normalize_args(["wake", "--as", "hailot"])
    assert result == ["wake", "--as", "hailot"]


def test_alias_preserve_non_identity_args():
    result = AliasResolver.normalize_args(["memory", "list", "--json"])
    # memory list is a subcommand, not identity alias
    assert result == ["memory", "list", "--json"]


def test_alias_resolve_command_path():
    routes = AliasResolver.get_routes("bridge")
    assert "bridge" in routes
    assert "bridge" in routes


def test_alias_supports_direct_shortcuts():
    ctx = AliasResolver.resolve(["wake", "--as", "hailot"])
    assert ctx.command == "wake"
    assert ctx.identity == "hailot"
