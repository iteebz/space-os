#!/usr/bin/env python3
"""Infer identity from message cwd field and link sessions to identities."""

from pathlib import Path

from space.lib import db as db_lib, providers
from space.core.chats import api, db

db.register()

print("Inferring identities from message cwd...\n")

with db_lib.ensure("chats") as conn:
    sessions = conn.execute(
        "SELECT cli, session_id, file_path FROM sessions WHERE identity IS NULL"
    ).fetchall()
    
    linked = 0
    for session in sessions:
        cli_name = session["cli"]
        session_id = session["session_id"]
        file_path = session["file_path"]
        
        if not Path(file_path).exists():
            continue
        
        try:
            provider = getattr(providers, cli_name, None)
            if not provider:
                continue
            
            messages = provider.parse_messages(Path(file_path))
            
            if messages:
                cwd = messages[0].get("cwd")
                if cwd:
                    api.linking.link(session_id, identity=cwd)
                    linked += 1
                    print(f"✓ {session_id[:8]} → {cwd}")
        except Exception as e:
            pass

print(f"\nLinked {linked} sessions to identity")
