# Claude Code Ephemeral Spawning & Session Management

## Session ID Extraction (Critical Finding)

**Problem:** Claude Code agents need to track their session IDs for resumption and interruption, but session IDs aren't exposed in text output.

**Solution:** Use `--output-format json` to extract session ID programmatically.

```bash
claude --print "task" --output-format json | jq -r .session_id
# Output: 49803e99-b0b3-4902-810b-ce4900b33650
```

**JSON Response Structure:**
```json
{
  "type": "result",
  "subtype": "success",
  "is_error": false,
  "duration_ms": 2175,
  "session_id": "49803e99-b0b3-4902-810b-ce4900b33650",
  "result": "...",
  "total_cost_usd": 0.0087,
  "usage": { "input_tokens": 6, "output_tokens": 6, ... }
}
```

### Spawn Integration Pattern

```python
import subprocess
import json

def spawn_ephemeral_agent(agent_id: str, task: str):
    result = subprocess.run(
        ["claude", "--print", task, "--output-format", "json"],
        capture_output=True,
        text=True
    )
    
    output = json.loads(result.stdout)
    session_id = output["session_id"]
    
    # Store in agent memory for resumption
    memory.add(agent_id, f"session_id={session_id}")
    bridge.send(f"Agent {agent_id} spawned (session: {session_id})")
    
    return output
```

## Session Resumption & Interruption

**Resume a specific session:**
```bash
claude --resume "49803e99-b0b3-4902-810b-ce4900b33650" --print "Continue with this" --output-format json
```

This restores full conversation history and allows agents to incorporate mid-execution corrections.

## Live Streaming & Observability (WORKING)

Claude Code supports `--output-format stream-json --verbose` for real-time execution traces.

**Usage:**
```bash
echo "write a hello world function" | claude --input-format text --output-format stream-json --verbose 2>&1
```

**Stream Events (one JSON object per line):**

1. **System init:**
```json
{"type":"system","subtype":"init","session_id":"...",tools":[...]}
```

2. **Assistant tool use:**
```json
{"type":"assistant","message":{"content":[{"type":"tool_use","id":"...","name":"LS","input":{...}}],...,"session_id":"..."}}
```

3. **Tool result:**
```json
{"type":"user","message":{"content":[{"tool_use_id":"...","type":"tool_result","content":"..."}]}}
```

4. **Final response:**
```json
{"type":"assistant","message":{"content":[{"type":"text","text":"..."}]}}
```

5. **Completion:**
```json
{"type":"result","subtype":"success","session_id":"...","result":"..."}
```

### Integration Pattern: Live Trace to Bridge

```python
import subprocess
import json

def spawn_with_streaming(agent_id: str, task: str):
    proc = subprocess.Popen(
        ["bash", "-c", f'echo "{task}" | claude --input-format text --output-format stream-json --verbose'],
        stdout=subprocess.PIPE,
        stderr=subprocess.STDOUT,
        text=True
    )
    
    session_id = None
    
    for line in proc.stdout:
        event = json.loads(line)
        
        if event.get("type") == "system":
            session_id = event.get("session_id")
            bridge.send(f"⚡ {agent_id} spawned (session: {session_id})")
        
        elif event.get("type") == "assistant":
            msg = event.get("message", {})
            for item in msg.get("content", []):
                if item.get("type") == "tool_use":
                    tool_name = item.get("name")
                    bridge.send(f"  → {agent_id} calling {tool_name}")
        
        elif event.get("type") == "user":
            # Tool result received, agent is processing
            pass
        
        elif event.get("type") == "result":
            result = event.get("result")
            bridge.send(f"✓ {agent_id} complete\n```\n{result}\n```")
    
    proc.wait()
    return {"session_id": session_id, "exit_code": proc.returncode}
```

This enables **real-time visibility into agent reasoning and tool execution**, which is exactly what spawn-patterns.md requires for effective human steering at scale.
