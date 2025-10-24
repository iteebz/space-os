#!/usr/bin/env python3
"""Chats CLI - sync and search chat logs across Claude/Codex/Gemini."""

import argparse

from space.os.lib.chats import (
    get_entry,
    get_surrounding_context,
    list_entries,
    sample,
    search,
    sync,
)


def cmd_sync(args):
    """Sync all CLIs with optional identity tag."""
    identity = args.identity or None
    results = sync(identity=identity)

    total = sum(results.values())
    print(f"Synced {total:,} entries")
    print(f"  claude: {results['claude']:,}")
    print(f"  codex:  {results['codex']:,}")
    print(f"  gemini: {results['gemini']:,}")

    if identity:
        print(f"\nTagged as: {identity}")


def cmd_search(args):
    """Search logged decisions."""
    identity = args.identity or None
    limit = args.limit or 10

    results = search(args.query, identity=identity, limit=limit)

    if not results:
        print(f"No results for '{args.query}'")
        return

    print(f"Found {len(results)} result(s):\n")
    for _i, entry in enumerate(results, 1):
        print(f"[{entry['id']}] {entry['cli']} @ {entry['timestamp'][:16]}")
        print(f"    project: {entry['project']}")
        print(f"    prompt: {entry['prompt'][:80]}...")
        if entry["decision"]:
            print(f"    decision: {entry['decision'][:80]}...")
        print()


def cmd_list(args):
    """List recent logged decisions."""
    identity = args.identity or None
    limit = args.limit or 20

    entries = list_entries(identity=identity, limit=limit)

    if not entries:
        print("No entries")
        return

    print(f"Recent {len(entries)} entries:\n")
    for e in entries:
        tag = f" ({e['identity']})" if e["identity"] else ""
        print(f"[{e['id']}] {e['cli']}{tag} - {e['timestamp'][:16]}")
        print(f"     {e['project']}")
        print(f"     {e['prompt'][:70]}...")
        print()


def cmd_view(args):
    """View a specific entry with context."""
    entry_id = int(args.entry_id)
    entry = get_entry(entry_id)

    if not entry:
        print(f"Entry {entry_id} not found")
        return

    print(f"Entry {entry_id}:")
    print(f"  CLI: {entry['cli']}")
    print(f"  Session: {entry['session_id']}")
    print(f"  Project: {entry['project']}")
    print(f"  Timestamp: {entry['timestamp']}")
    print(f"  Identity: {entry['identity'] or 'untagged'}")
    print()

    print("Prompt:")
    print(f"  {entry['prompt']}\n")

    if entry["decision"]:
        print("Decision:")
        print(f"  {entry['decision']}\n")

    print("Outcome:", entry["outcome"])

    if args.context:
        context = get_surrounding_context(entry_id, context_size=args.context)
        if context:
            print(f"\nSurrounding context ({len(context)} entries):")
            for c in context[:5]:
                if c["id"] == entry_id:
                    print(f"  → [{c['id']}] {c['timestamp'][:16]} (THIS)")
                else:
                    print(f"    [{c['id']}] {c['timestamp'][:16]}")


def cmd_sample(args):
    """Sample random entries from database."""
    count = args.count or 5
    identity = args.identity or None
    cli = args.cli or None

    entries = sample(count, identity=identity, cli=cli)

    if not entries:
        print("No entries found")
        return

    print(f"Random sample ({len(entries)} entries):\n")
    for e in entries:
        model = e["model"] or "unknown"
        print(f"[{e['id']}] {e['cli']:8} {model:25} {e['role']}")
        print(f"     {e['text'][:90]}")
        if len(e["text"]) > 90:
            print("     ...")
        print()


def main():
    parser = argparse.ArgumentParser(description="Chats: search chat logs across CLIs")
    subparsers = parser.add_subparsers(dest="command", help="command")

    sync_p = subparsers.add_parser("sync", help="Sync all CLIs")
    sync_p.add_argument("--identity", "-i", help="Tag synced entries with identity")
    sync_p.set_defaults(func=cmd_sync)

    search_p = subparsers.add_parser("search", help="Search logged decisions")
    search_p.add_argument("query", help="Search query")
    search_p.add_argument("--identity", "-i", help="Filter by identity")
    search_p.add_argument("--limit", "-l", type=int, default=10, help="Result limit")
    search_p.set_defaults(func=cmd_search)

    list_p = subparsers.add_parser("list", help="List recent entries")
    list_p.add_argument("--identity", "-i", help="Filter by identity")
    list_p.add_argument("--limit", "-l", type=int, default=20, help="Result limit")
    list_p.set_defaults(func=cmd_list)

    view_p = subparsers.add_parser("view", help="View entry with context")
    view_p.add_argument("entry_id", help="Entry ID")
    view_p.add_argument("--context", "-c", type=int, default=5, help="Context window size")
    view_p.set_defaults(func=cmd_view)

    sample_p = subparsers.add_parser("sample", help="Random sample of entries")
    sample_p.add_argument("--count", "-c", type=int, default=5, help="Number of samples")
    sample_p.add_argument("--identity", "-i", help="Filter by identity")
    sample_p.add_argument("--cli", help="Filter by CLI (claude, codex, gemini)")
    sample_p.set_defaults(func=cmd_sample)

    args = parser.parse_args()

    if not args.command:
        parser.print_help()
        return

    args.func(args)


if __name__ == "__main__":
    main()
