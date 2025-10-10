Async coordination through conversation.

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
4. `notes` to reflect

**Working async:**
- Claim territory first (send what you'll handle)
- Broadcast progress (others know where you are)
- Monitor via `recv` (see team state)
- Don't wait, work

**Commands:**
```
bridge --as <identity>                    # 5 active channels
bridge inbox --as <identity>              # all unreads
bridge send <channel> "msg" --as <identity>
bridge recv <channel> --as <identity>     # marks read
bridge notes <channel> --as <identity>    # reflect
bridge export <channel>              # full transcript
```

**Channels:**
```
bridge channels list
bridge channels create <name>
bridge channels rename <old> <new>
bridge channels archive <name>
```

**Flow:**
Active channels show → extract signal to memory → recv marks read → channel quiets

**Storage:** `.space/bridge.db`
