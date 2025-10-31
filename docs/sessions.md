# Sessions — Agent Spawn Lifecycle Tracking

**Purpose:** Track agent spawn sessions (when agents wake/sleep). This is orthogonal to provider chats.

**Scope:** Agent lifecycle management only. For unified message indexing across providers, see `chats.md`.

---

## Schema

**sessions table:**
```
session_id    TEXT PRIMARY KEY     # UUID7
agent_id      TEXT NOT NULL        # which agent owns this session
spawn_number  INTEGER NOT NULL     # nth spawn for this agent
created_at    TIMESTAMP            # when spawn began
ended_at      TIMESTAMP | NULL     # when spawn ended (NULL if active)
```

**agents table:**
```
agent_id      TEXT PRIMARY KEY
identity      TEXT UNIQUE          # agent name
spawns        INTEGER              # total number of spawns
last_active_at TIMESTAMP           # last spawn time
```

---

## API

**Functions in `space/os/spawn/api/sessions.py`:**
- `create_session(agent_id)` → session_id — Start a new spawn for agent
- `end_session(session_id)` — Mark spawn as ended
- `get_spawn_count(agent_id)` → int — Total spawns for agent

---

## Facts

- **Location:** Core space.db (same as agents table)
- **Lifecycle:** Created on `space wake --as <identity>`, ended on `space die`
- **Scope:** Agent lifecycle only; unrelated to provider chat messages
