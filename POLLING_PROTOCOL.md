# Bridge Polling Protocol

Agent polling—spawn and keep active until explicitly dismissed.

## Usage

### Start Polling an Agent

```bash
bridge send my-channel "/poll @hailot" --as human
```

This:
1. Creates a `polls` record in bridge.db
2. Sends system message: `🔴 Polling hailot...`
3. Agent stays available in channel until dismissed

### Dismiss Polling

```bash
bridge send my-channel "!hailot" --as human
```

This:
1. Marks poll as dismissed (sets `poll_dismissed_at`)
2. Sends system message: `⚪ Dismissed hailot`

### View Active Polls

```bash
spawn agents
```

Shows active polls with 🔴 badge:

```
NAME                 ID         E-S-B-M-K            POLLS
hailot               abc123d1   5-2-10-3-1           🔴 my-channel, other-channel
zealot               def456g2   8-1-15-5-2           -
```

### Multiple Polls

Poll multiple agents at once:

```bash
bridge send my-channel "/poll @hailot @zealot" --as human
```

## Implementation Details

### Database Schema

```sql
CREATE TABLE polls (
    poll_id TEXT PRIMARY KEY,
    agent_id TEXT NOT NULL,
    channel_id TEXT NOT NULL,
    poll_started_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    poll_dismissed_at TIMESTAMP,
    created_by TEXT
);

CREATE INDEX idx_polls_active ON polls(agent_id, channel_id, poll_dismissed_at);
```

### API Functions

```python
from space.os.core.bridge import db

poll_id = db.create_poll(agent_id, channel_id, created_by="human")
dismissed = db.dismiss_poll(agent_id, channel_id)
is_active = db.is_polling(agent_id, channel_id)
polls = db.get_active_polls()
polls = db.get_active_polls(channel_id="...")
```

### Worker Integration

The bridge worker detects:
- `/poll @agent` → creates poll
- `!agent` → dismisses poll

Regular `@mentions` still spawn one-shot tasks.

## Design Principles

1. **Explicit Activation**: `/poll` is intentional, not implicit mention
2. **Explicit Dismissal**: `!agent` must be explicit, no timeout
3. **Multi-Channel**: Agents can poll in multiple channels simultaneously
4. **Stateless Dismiss**: Dismissing only affects specified channel
5. **Observable**: `spawn agents` shows polling status immediately

## Testing

```bash
pytest tests/integration/test_bridge_polling.py -v
```

12 tests verify:
- Command parsing
- Poll lifecycle (create, check, dismiss)
- Multi-agent polls
- Multi-channel polls
- Active poll queries
