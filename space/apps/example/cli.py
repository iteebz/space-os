import click

@click.group()
def example_group():
    """Example app CLI."""
    pass

@example_group.command("reverse")
@click.argument("text")
def reverse_command(text):
    """Reverses a given string."""
    from .api import reverse_string # Import here to avoid circular dependency if cli.py is imported by __init__.py
    click.echo(reverse_string(text))
