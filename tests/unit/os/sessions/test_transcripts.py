"""Transcript indexing and search tests: contracts, boundaries, integration."""

import json

from space.lib import store
from space.os.sessions.api import operations, sync


class TestIndexTranscripts:
    """_index_transcripts() contract: parse JSONL, filter role, convert timestamps."""

    def test_filters_role_and_converts_timestamps(self):
        """Only user/assistant indexed. ISO8601 → unix epoch."""
        sid = "test-idx-role-ts"
        with store.ensure() as conn:
            conn.execute(
                "INSERT INTO sessions (session_id, provider, model) VALUES (?, ?, ?)",
                (sid, "claude", "test"),
            )
            conn.commit()

        jsonl = "\n".join(
            [
                json.dumps(
                    {"role": "user", "content": "hello", "timestamp": "2025-11-01T10:00:00Z"}
                ),
                json.dumps(
                    {"role": "assistant", "content": "hi", "timestamp": "2025-11-01T10:00:10Z"}
                ),
                json.dumps(
                    {"role": "tool", "content": "skip me", "timestamp": "2025-11-01T10:00:20Z"}
                ),
            ]
        )

        with store.ensure() as conn:
            count = sync._index_transcripts(sid, "claude", jsonl, conn)
            conn.commit()
        assert count == 2

        with store.ensure() as conn:
            rows = conn.execute(
                "SELECT role, timestamp FROM transcripts WHERE session_id = ?", (sid,)
            ).fetchall()
            assert len(rows) == 2
            assert all(isinstance(r[1], int) for r in rows)

        # Cleanup
        with store.ensure() as conn:
            conn.execute("DELETE FROM transcripts WHERE session_id = ?", (sid,))
            conn.execute("DELETE FROM sessions WHERE session_id = ?", (sid,))
            conn.commit()

    def test_handles_content_arrays(self):
        """Text arrays joined properly."""
        sid = "test-arrays"
        with store.ensure() as conn:
            conn.execute(
                "INSERT INTO sessions (session_id, provider, model) VALUES (?, ?, ?)",
                (sid, "claude", "test"),
            )
            conn.commit()

        jsonl = json.dumps(
            {
                "role": "assistant",
                "content": [
                    {"type": "text", "text": "Block1"},
                    {"type": "text", "text": "Block2"},
                ],
                "timestamp": "2025-11-01T10:00:00Z",
            }
        )

        with store.ensure() as conn:
            sync._index_transcripts(sid, "claude", jsonl, conn)
            conn.commit()

        with store.ensure() as conn:
            content = conn.execute(
                "SELECT content FROM transcripts WHERE session_id = ?", (sid,)
            ).fetchone()[0]
            assert "Block1" in content and "Block2" in content

        # Cleanup
        with store.ensure() as conn:
            conn.execute("DELETE FROM transcripts WHERE session_id = ?", (sid,))
            conn.execute("DELETE FROM sessions WHERE session_id = ?", (sid,))
            conn.commit()

    def test_skips_empty_and_malformed(self):
        """Empty content and malformed JSON gracefully handled."""
        sid = "test-empty-malformed"
        with store.ensure() as conn:
            conn.execute(
                "INSERT INTO sessions (session_id, provider, model) VALUES (?, ?, ?)",
                (sid, "claude", "test"),
            )
            conn.commit()

        jsonl = "\n".join(
            [
                json.dumps({"role": "user", "content": "", "timestamp": "2025-11-01T10:00:00Z"}),
                "not json",
                json.dumps(
                    {"role": "user", "content": "valid", "timestamp": "2025-11-01T10:00:10Z"}
                ),
            ]
        )

        with store.ensure() as conn:
            count = sync._index_transcripts(sid, "claude", jsonl, conn)
            conn.commit()
        assert count == 1

        # Cleanup
        with store.ensure() as conn:
            conn.execute("DELETE FROM transcripts WHERE session_id = ?", (sid,))
            conn.execute("DELETE FROM sessions WHERE session_id = ?", (sid,))
            conn.commit()


class TestSearch:
    """search() boundary: FTS5 query execution, result shape."""

    def test_search_returns_correct_shape(self):
        """Result has: source, cli, session_id, role, text, timestamp, reference."""
        sid = "test-shape-xyz"
        with store.ensure() as conn:
            conn.execute(
                "INSERT INTO sessions (session_id, provider, model) VALUES (?, ?, ?)",
                (sid, "claude", "test"),
            )
            conn.execute(
                """
                INSERT INTO transcripts (session_id, message_index, provider, role, content, timestamp)
                VALUES (?, ?, ?, ?, ?, ?)
            """,
                (sid, 0, "claude", "user", "spawn registry pattern shape xyz", 1698900000),
            )
            conn.commit()

        results = [r for r in operations.search("shape xyz") if r["session_id"] == sid]
        assert len(results) == 1

        result = results[0]
        assert result["source"] == "chat"
        assert result["cli"] == "claude"
        assert result["session_id"] == sid
        assert result["role"] == "user"
        assert isinstance(result["timestamp"], int)
        assert "reference" in result

        # Cleanup
        with store.ensure() as conn:
            conn.execute("DELETE FROM transcripts WHERE session_id = ?", (sid,))
            conn.execute("DELETE FROM sessions WHERE session_id = ?", (sid,))
            conn.commit()

    def test_search_fts5_syntax(self):
        """FTS5 phrase and boolean queries work."""
        sid = "test-fts-syntax-unique-123"
        with store.ensure() as conn:
            conn.execute("DELETE FROM transcripts WHERE session_id = ?", (sid,))
            conn.execute("DELETE FROM sessions WHERE session_id = ?", (sid,))
            conn.execute(
                "INSERT INTO sessions (session_id, provider, model) VALUES (?, ?, ?)",
                (sid, "claude", "test"),
            )
            conn.execute(
                """
                INSERT INTO transcripts (session_id, message_index, provider, role, content, timestamp)
                VALUES (?, ?, ?, ?, ?, ?)
            """,
                (sid, 0, "claude", "user", "constitutional diversity governance unique", 1698900000),
            )
            conn.execute(
                """
                INSERT INTO transcripts (session_id, message_index, provider, role, content, timestamp)
                VALUES (?, ?, ?, ?, ?, ?)
            """,
                (sid, 1, "claude", "user", "just diversity here", 1698900010),
            )
            conn.commit()

        # Phrase search (triggers index automatically)
        results = [
            r for r in operations.search('"constitutional diversity"') if r["session_id"] == sid
        ]
        assert len(results) >= 1

        # Boolean AND
        results = [
            r for r in operations.search("constitutional AND governance") if r["session_id"] == sid
        ]
        assert len(results) >= 1

        # Cleanup
        with store.ensure() as conn:
            conn.execute("DELETE FROM transcripts WHERE session_id = ?", (sid,))
            conn.execute("DELETE FROM sessions WHERE session_id = ?", (sid,))
            conn.commit()


class TestIntegration:
    """sync→index→search→context chain."""

    def test_sync_indexes_and_search_finds(self):
        """Transcripts indexed after sync, search returns results."""
        sid = "test-chain-integration"
        with store.ensure() as conn:
            conn.execute(
                "INSERT INTO sessions (session_id, provider, model) VALUES (?, ?, ?)",
                (sid, "claude", "test"),
            )
            conn.commit()

        jsonl = "\n".join(
            [
                json.dumps(
                    {
                        "role": "user",
                        "content": "spawn registry design integration",
                        "timestamp": "2025-11-01T10:00:00Z",
                    }
                ),
                json.dumps(
                    {
                        "role": "assistant",
                        "content": "spawn registry is core integration",
                        "timestamp": "2025-11-01T10:00:10Z",
                    }
                ),
            ]
        )

        with store.ensure() as conn:
            sync._index_transcripts(sid, "claude", jsonl, conn)
            conn.commit()

        results = [r for r in operations.search("integration") if r["session_id"] == sid]
        assert len(results) == 2
        assert all(sid == r["session_id"] for r in results)

        # Cleanup
        with store.ensure() as conn:
            conn.execute("DELETE FROM transcripts WHERE session_id = ?", (sid,))
            conn.execute("DELETE FROM sessions WHERE session_id = ?", (sid,))
            conn.commit()

    def test_fts5_triggers_keep_index_in_sync(self):
        """INSERT/DELETE auto-triggers FTS5 updates."""
        sid = "test-triggers"
        with store.ensure() as conn:
            conn.execute(
                "INSERT INTO sessions (session_id, provider, model) VALUES (?, ?, ?)",
                (sid, "claude", "test"),
            )
            conn.execute(
                """
                INSERT INTO transcripts (session_id, message_index, provider, role, content, timestamp)
                VALUES (?, ?, ?, ?, ?, ?)
            """,
                (sid, 0, "claude", "user", "trigger test message", 1698900000),
            )
            conn.commit()

        # Searchable
        assert len(operations.search("trigger")) == 1

        # Delete and gone
        with store.ensure() as conn:
            conn.execute("DELETE FROM transcripts WHERE session_id = ?", (sid,))
            conn.commit()

        assert len(operations.search("trigger")) == 0

        # Cleanup
        with store.ensure() as conn:
            conn.execute("DELETE FROM sessions WHERE session_id = ?", (sid,))
            conn.commit()

    def test_context_includes_sessions(self):
        """Context search includes session results."""
        from space.apps.context.api import collect_current_state

        sid = "test-context"
        with store.ensure() as conn:
            conn.execute(
                "INSERT INTO sessions (session_id, provider, model) VALUES (?, ?, ?)",
                (sid, "claude", "test"),
            )
            conn.execute(
                """
                INSERT INTO transcripts (session_id, message_index, provider, role, content, timestamp)
                VALUES (?, ?, ?, ?, ?, ?)
            """,
                (sid, 0, "claude", "user", "context search works", 1698900000),
            )
            conn.commit()

        state = collect_current_state("context search", None, False)
        results = state.get("sessions", [])

        assert len(results) > 0
        assert any("search" in r.get("text", "") for r in results)

        # Cleanup
        with store.ensure() as conn:
            conn.execute("DELETE FROM transcripts WHERE session_id = ?", (sid,))
            conn.execute("DELETE FROM sessions WHERE session_id = ?", (sid,))
            conn.commit()
