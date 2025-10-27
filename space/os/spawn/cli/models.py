"""List available models command."""

import typer

from space.os.spawn import models as models_module


def list_models():
    """List available models for all providers."""
    for prov in ["claude", "codex", "gemini"]:
        provider_models = models_module.get_models_for_provider(prov)
        typer.echo(f"\n📦 {prov.capitalize()} Models:\n")
        for model in provider_models:
            typer.echo(f"  • {model.name} ({model.id})")
            if model.description:
                typer.echo(f"    {model.description}")
            if model.reasoning_levels:
                typer.echo(f"    Reasoning levels: {', '.join(model.reasoning_levels)}")
            typer.echo()
