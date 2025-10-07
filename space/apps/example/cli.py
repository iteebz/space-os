import click

from . import reverse_string


@click.group()
def example_group():
    """Example app CLI."""
    pass


@example_group.command("reverse")
@click.argument("text")
def reverse_command(text):
    """Reverses a given string."""
    click.echo(reverse_string(text))