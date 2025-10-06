import click
from typing import Protocol, runtime_checkable

from space.protocols import App

def test_app_protocol_conformance():
    """
    Tests that a class implementing the App protocol is recognized as conforming.
    """
    class ConformingApp:
        @property
        def name(self) -> str:
            return "test_app"

        def cli_group(self) -> click.Group:
            @click.group()
            def test_group():
                pass
            return test_group

    app_instance = ConformingApp()
    assert isinstance(app_instance, App)

def test_app_protocol_non_conformance_missing_name():
    """
    Tests that a class missing the 'name' property does not conform to App protocol.
    """
    class NonConformingAppMissingName:
        def cli_group(self) -> click.Group:
            @click.group()
            def test_group():
                pass
            return test_group

    app_instance = NonConformingAppMissingName()
    assert not isinstance(app_instance, App)

def test_app_protocol_non_conformance_missing_cli_group():
    """
    Tests that a class missing the 'cli_group' method does not conform to App protocol.
    """
    class NonConformingAppMissingCliGroup:
        @property
        def name(self) -> str:
            return "test_app"

    app_instance = NonConformingAppMissingCliGroup()
    assert not isinstance(app_instance, App)
