# Polling Protocol Examples

## Example: Council Session with Agent on Standby

### Start polling agent in council

```bash
# User in council joins the channel
bridge send space-dev "/poll @hailot" --as human
```

System message appears:
```
🔴 Polling hailot...
```

### Check active polls anytime

```bash
spawn agents
```

Output shows:
```
NAME                 ID         E-S-B-M-K            POLLS
hailot               abc123d1   5-2-10-3-1           🔴 space-dev
```

### Dismiss when done

```bash
bridge send space-dev "!hailot" --as human
```

System message:
```
⚪ Dismissed hailot
```

Poll is gone from `spawn agents`:
```
NAME                 ID         E-S-B-M-K            POLLS
hailot               abc123d1   5-2-10-3-1           -
```

---

## Example: Multiple Agents on Call

```bash
bridge send architecture-review "/poll @zealot @harbinger" --as human
```

Both agents now active in that channel:
```
🔴 Polling zealot...
🔴 Polling harbinger...
```

Show status:
```bash
spawn agents
```

```
zealot               zea789x3   8-1-15-5-2           🔴 architecture-review
harbinger           hab456k2   3-5-8-2-1            🔴 architecture-review
hailot               abc123d1   5-2-10-3-1           -
```

Dismiss just one:
```bash
bridge send architecture-review "!zealot" --as human
```

Harbinger stays active:
```
zealot               zea789x3   8-1-15-5-2           -
harbinger           hab456k2   3-5-8-2-1            🔴 architecture-review
```

---

## Example: Polling in Multiple Channels Simultaneously

Same agent can poll in different channels:

```bash
bridge send space-dev "/poll @hailot" --as human
bridge send budgets "/poll @hailot" --as human
```

Check status:
```bash
spawn agents
```

```
hailot               abc123d1   5-2-10-3-1           🔴 budgets, space-dev
```

---

## Difference: Polling vs Mention

### Regular mention (one-shot task):
```bash
bridge send dev "@hailot what is 2+2?" --as human
```
- Spawns agent one time
- Returns output
- Agent exits

### Polling (stay active):
```bash
bridge send dev "/poll @hailot" --as human
```
- Creates persistent poll
- Agent stays in channel
- Remains active until `!hailot`
- Can respond to follow-ups

---

## API Usage

```python
from space.os.core.bridge import db
from space.os.core.spawn import db as spawn_db

agent_id = spawn_db.ensure_agent("hailot")
channel_id = db.resolve_channel_id("space-dev")

poll_id = db.create_poll(agent_id, channel_id, created_by="human")
print(f"Polling: {db.is_polling(agent_id, channel_id)}")

polls = db.get_active_polls(channel_id=channel_id)
for p in polls:
    print(f"  - {p['agent_id']}")

db.dismiss_poll(agent_id, channel_id)
print(f"Polling: {db.is_polling(agent_id, channel_id)}")
```
