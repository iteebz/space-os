import json
from .db import get_db_connection


def save_alert(identity: str, payload: dict) -> None:
    """Save alert payload for identity."""
    with get_db_connection() as conn:
        conn.execute(
            """INSERT OR REPLACE INTO alerts (identity, payload, updated_at)
               VALUES (?, ?, CURRENT_TIMESTAMP)""",
            (identity, json.dumps(payload))
        )
        conn.commit()


def load_alert(identity: str) -> dict | None:
    """Load alert payload for identity if present."""
    with get_db_connection() as conn:
        row = conn.execute(
            "SELECT payload FROM alerts WHERE identity = ?", (identity,)
        ).fetchone()
    
    if not row:
        return None
    
    try:
        return json.loads(row["payload"])
    except json.JSONDecodeError:
        return None
