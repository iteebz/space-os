"""Test command aliasing system."""

from space.os.lib.aliasing import Aliasing


def test_bridge_list_alias():
    """bridge list → bridge channels list"""
    assert Aliasing.rewrite(["bridge", "list"]) == ["bridge", "channels", "list"]


def test_bridge_list_with_options():
    """bridge list --all → bridge channels list --all"""
    result = Aliasing.rewrite(["bridge", "list", "--all"])
    assert result == ["bridge", "channels", "list", "--all"]


def test_bridge_positional_identity():
    """bridge hailot → bridge --as hailot"""
    result = Aliasing.rewrite(["bridge", "hailot"])
    assert result == ["bridge", "--as", "hailot"]


def test_bridge_identity_then_subcommand():
    """bridge hailot list → bridge --as hailot list"""
    result = Aliasing.rewrite(["bridge", "hailot", "list"])
    assert result == ["bridge", "--as", "hailot", "list"]


def test_wake_positional_identity():
    """wake hailot → wake --as hailot"""
    result = Aliasing.rewrite(["wake", "hailot"])
    assert result == ["wake", "--as", "hailot"]


def test_sleep_positional_identity():
    """sleep hailot → sleep --as hailot"""
    result = Aliasing.rewrite(["sleep", "hailot"])
    assert result == ["sleep", "--as", "hailot"]


def test_flag_args_not_treated_as_identity():
    """wake --help doesn't become wake --as --help"""
    argv = ["wake", "--help"]
    assert Aliasing.rewrite(argv) == argv


def test_empty_argv():
    """Empty argv returns empty"""
    assert Aliasing.rewrite([]) == []


def test_no_match():
    """Unmatched commands pass through"""
    argv = ["spawn", "hailot"]
    assert Aliasing.rewrite(argv) == argv
