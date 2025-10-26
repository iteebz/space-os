#!/usr/bin/env python3
"""Exploratory data analysis on normalized chats.db."""

from datetime import datetime

from space.core.chats import db

db.register()

print("Chats EDA\n")

with store.ensure("chats") as conn:
    # Claude age distribution + deletion risk
    print("Claude Sessions by Age:")
    now = datetime.now()

    claude_sessions = conn.execute(
        "SELECT discovered_at FROM sessions WHERE cli = 'claude' ORDER BY discovered_at ASC"
    ).fetchall()

    if claude_sessions:
        ages = []
        for row in claude_sessions:
            discovered = datetime.fromisoformat(row["discovered_at"])
            age_days = (now - discovered).days
            ages.append(age_days)

        deletion_risk = sum(1 for age in ages if age >= 25)
        print(f"  Total: {len(ages)} sessions")
        print(f"  At deletion risk (25+ days): {deletion_risk}")
        print(f"  Age range: {min(ages)}-{max(ages)} days")
        print(f"  First session: {ages[0]} days ago")

    # Message counts per provider
    print("\nMessage Counts (from messages table):")
    msg_stats = conn.execute(
        "SELECT cli, COUNT(*) as count FROM messages GROUP BY cli ORDER BY cli"
    ).fetchall()

    total_msgs = 0
    for row in msg_stats:
        cli = row["cli"].capitalize()
        count = row["count"]
        total_msgs += count
        print(f"  {cli}: {count} messages")

    print(f"  Total: {total_msgs} messages")

    # Message distribution by role
    print("\nMessages by Role:")
    role_stats = conn.execute(
        "SELECT role, COUNT(*) as count FROM messages GROUP BY role ORDER BY count DESC"
    ).fetchall()

    for row in role_stats:
        role = row["role"]
        count = row["count"]
        pct = (count / total_msgs * 100) if total_msgs > 0 else 0
        print(f"  {role}: {count} ({pct:.1f}%)")

    # Temporal distribution
    print("\nTemporal Coverage:")
    time_range = conn.execute(
        "SELECT MIN(timestamp) as first, MAX(timestamp) as last FROM messages"
    ).fetchone()

    if time_range and time_range["first"]:
        print(f"  First message: {time_range['first']}")
        print(f"  Last message: {time_range['last']}")

    # Daily message volume
    print("\nDaily Message Volume (sample):")
    daily = conn.execute(
        """
        SELECT DATE(timestamp) as day, COUNT(*) as count
        FROM messages
        WHERE timestamp IS NOT NULL
        GROUP BY DATE(timestamp)
        ORDER BY day DESC
        LIMIT 7
        """
    ).fetchall()

    for row in daily:
        print(f"  {row['day']}: {row['count']} messages")

    # Tool invocations
    print("\nTool Usage:")
    tool_count = conn.execute(
        "SELECT COUNT(*) as count FROM messages WHERE tool_type IS NOT NULL"
    ).fetchone()
    print(f"  Tool messages: {tool_count['count']}")

    # CWD diversity (Claude only)
    print("\nCWD Diversity (Claude):")
    cwd_count = conn.execute(
        "SELECT COUNT(DISTINCT cwd) as count FROM messages WHERE cli = 'claude' AND cwd IS NOT NULL"
    ).fetchone()
    print(f"  Unique working dirs: {cwd_count['count']}")

    # Average messages per session
    print("\nMessages per Session:")
    session_avg = conn.execute(
        """
        SELECT cli,
               COUNT(DISTINCT session_id) as sessions,
               COUNT(*) as total_msgs,
               ROUND(CAST(COUNT(*) AS FLOAT) / COUNT(DISTINCT session_id), 2) as avg
        FROM messages
        GROUP BY cli
        ORDER BY cli
        """
    ).fetchall()

    for row in session_avg:
        cli = row["cli"].capitalize()
        print(
            f"  {cli}: {row['avg']} msgs/session ({row['total_msgs']} msgs / {row['sessions']} sessions)"
        )
