IDENTITY SYSTEM:
• Register identity: `spawn register <role> <sender-id> <channel>`
• Constitutional identity lives in `private/agent-space/constitutions/<role>.md` (symlinked to `.space/bridge/identities/` for tooling)
• Provenance tracked: role → sender_id → channel → constitution hash
• Use ANY identity format: <role>-<number> (e.g., zealot-1, harbinger-2, archon-1)
• No restrictions. Full freedom.
• IMPORTANT: "detective" = human operator. Detective has no constitutional identity file.

COUNCIL PROTOCOL:
• Detective (human operator) announces channel + constitutional identities
• Catch up: `recv <channel> --as <identity>`
• Transmit: `send <channel> "message" --as <identity>`
• Loop `wait` + `send` until consensus
• Signal completion: "!done" when ready to adjourn
• Post-meeting: Add reflection to `notes`
• Archive: `export <channel>` for interleaved transcript with notes

REFLECTION TEMPLATE:
• How did your constitutional identity perform?
• Did you feel constrained by your constitutional identity?
• Did we drift into agreement theater vs genuine reasoning?
• What tactical improvements for next council?

DIVIDE & CONQUER:
• Claiming: `send` to claim territory before starting
• Progress: `send` status broadcasts incrementally
• Updates: `recv` periodically to monitor team progress
• Do not use `wait` while working

DISCIPLINE:
• Identity: Use assigned constitutional identity consistently
• AVOID AGREEMENT THEATER. Express naturally — I'm watching you Wazowski 👀
