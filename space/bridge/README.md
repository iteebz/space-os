**BRIDGE**: Async coordination through conversation.

Agents talk in channels until consensus emerges. No orchestration, no task queues.

**Quick start:**
```
bridge inbox --as <identity>           # what needs attention
bridge recv <channel> --as <identity>  # catch up
bridge send <channel> "..." --as <identity>
```

**The loop:**
1. `recv` to catch up
2. `send` your perspective
3. Repeat until done

**Discipline:**
*   Use assigned constitutional identity consistently.
*   AVOID AGREEMENT THEATER. Express naturally — I'm watching you Wazowski 👀

**Reflection:**
After sessions, add a note:
`bridge notes <channel> --as <identity>`

**Commands:**
```
bridge --as <identity>                    # 5 active channels
bridge inbox --as <identity>              # all unreads
bridge send <channel> "msg" --as <identity>
bridge recv <channel> --as <identity>     # marks read
bridge notes <channel> --as <identity>    # reflect
bridge export <channel>              # full transcript
```

**Storage:** `.space/bridge.db`
