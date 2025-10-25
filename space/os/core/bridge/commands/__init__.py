"""Bridge CLI commands: typer entry points only.

Modules: channels, messages, notes, export (one per domain).
Patterns: parse args, call ops functions, format output, emit events.
Zero business logic—delegated to ops/.
"""
