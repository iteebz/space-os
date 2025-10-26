"""Unit tests for SQL query builder helpers."""

from unittest.mock import MagicMock

from space.lib import query


def test_agent_by_name_active_only():
    """agent_by_name filters archived by default."""
    conn = MagicMock()
    conn.execute.return_value.fetchall.return_value = [{"agent_id": "id-1"}, {"agent_id": "id-2"}]

    result = query.agent_by_name(conn, "alice")
    assert result == ["id-1", "id-2"]

    call_args = conn.execute.call_args[0]
    assert "archived_at IS NULL" in call_args[0]


def test_agent_by_name_show_all():
    """agent_by_name includes archived when show_all=True."""
    conn = MagicMock()
    conn.execute.return_value.fetchall.return_value = [{"agent_id": "id-1"}]

    result = query.agent_by_name(conn, "alice", show_all=True)
    assert result == ["id-1"]

    call_args = conn.execute.call_args[0]
    assert "archived_at" not in call_args[0]


def test_agent_by_id():
    """agent_by_id returns agent name."""
    conn = MagicMock()
    conn.execute.return_value.fetchone.return_value = {"name": "alice"}

    result = query.agent_by_id(conn, "id-1")
    assert result == "alice"


def test_agent_by_id_not_found():
    """agent_by_id returns None if agent not found."""
    conn = MagicMock()
    conn.execute.return_value.fetchone.return_value = None

    result = query.agent_by_id(conn, "missing-id")
    assert result is None


def test_count_table():
    """count_table returns row count."""
    conn = MagicMock()
    conn.execute.return_value.fetchone.return_value = (42,)

    result = query.count_table(conn, "agents")
    assert result == 42
    assert "SELECT COUNT(*)" in conn.execute.call_args[0][0]


def test_count_table_with_where():
    """count_table applies WHERE clause."""
    conn = MagicMock()
    conn.execute.return_value.fetchone.return_value = (5,)

    result = query.count_table(conn, "agents", where="status = 'active'")
    assert result == 5

    call_args = conn.execute.call_args[0][0]
    assert "WHERE status = 'active'" in call_args


def test_count_active():
    """count_active counts non-archived."""
    conn = MagicMock()
    conn.execute.return_value.fetchone.return_value = (10,)

    query.count_active(conn, "agents")
    call_args = conn.execute.call_args[0][0]
    assert "archived_at IS NULL" in call_args


def test_count_active_with_where():
    """count_active combines archived and where filters."""
    conn = MagicMock()
    conn.execute.return_value.fetchone.return_value = (5,)

    query.count_active(conn, "agents", where="type = 'sentinel'")
    call_args = conn.execute.call_args[0][0]
    assert "archived_at IS NULL" in call_args
    assert "type = 'sentinel'" in call_args


def test_count_archived():
    """count_archived counts archived only."""
    conn = MagicMock()
    conn.execute.return_value.fetchone.return_value = (3,)

    query.count_archived(conn, "agents")
    call_args = conn.execute.call_args[0][0]
    assert "archived_at IS NOT NULL" in call_args


def test_select_with_filter_all_columns():
    """select_with_filter selects all columns by default."""
    conn = MagicMock()
    conn.execute.return_value.fetchall.return_value = [{"id": "1"}]

    query.select_with_filter(conn, "agents")
    call_args = conn.execute.call_args[0][0]
    assert "SELECT *" in call_args


def test_select_with_filter_specific_columns():
    """select_with_filter selects specific columns."""
    conn = MagicMock()
    conn.execute.return_value.fetchall.return_value = []

    query.select_with_filter(conn, "agents", columns="id, name")
    call_args = conn.execute.call_args[0][0]
    assert "SELECT id, name" in call_args


def test_select_with_filter_archive_filter():
    """select_with_filter filters archived by default."""
    conn = MagicMock()
    conn.execute.return_value.fetchall.return_value = []

    query.select_with_filter(conn, "agents", show_all=False)
    call_args = conn.execute.call_args[0][0]
    assert "archived_at IS NULL" in call_args


def test_select_with_filter_where_clause():
    """select_with_filter applies WHERE clause."""
    conn = MagicMock()
    conn.execute.return_value.fetchall.return_value = []

    query.select_with_filter(conn, "agents", where="type = ?")
    call_args = conn.execute.call_args[0][0]
    assert "WHERE" in call_args


def test_select_with_filter_order_by():
    """select_with_filter applies ORDER BY."""
    conn = MagicMock()
    conn.execute.return_value.fetchall.return_value = []

    query.select_with_filter(conn, "agents", order_by="ORDER BY created_at DESC")
    call_args = conn.execute.call_args[0][0]
    assert "ORDER BY created_at DESC" in call_args


def test_select_with_filter_limit():
    """select_with_filter applies LIMIT."""
    conn = MagicMock()
    conn.execute.return_value.fetchall.return_value = []

    query.select_with_filter(conn, "agents", limit=10)
    call_args = conn.execute.call_args[0][0]
    assert "LIMIT 10" in call_args


def test_select_distinct():
    """select_distinct returns distinct column values."""
    conn = MagicMock()
    conn.execute.return_value.fetchall.return_value = [("alice",), ("bob",), ("charlie",)]

    result = query.select_distinct(conn, "agents", "name")
    assert result == ["alice", "bob", "charlie"]


def test_select_distinct_with_archive_filter():
    """select_distinct filters archived by default."""
    conn = MagicMock()
    conn.execute.return_value.fetchall.return_value = []

    query.select_distinct(conn, "agents", "name", show_all=False)
    call_args = conn.execute.call_args[0][0]
    assert "archived_at IS NULL" in call_args


def test_count_by_group():
    """count_by_group returns group and count tuples."""
    conn = MagicMock()
    conn.execute.return_value.fetchall.return_value = [("alice", 5), ("bob", 3), ("charlie", 1)]

    result = query.count_by_group(conn, "tasks", "agent_id")
    assert result == [("alice", 5), ("bob", 3), ("charlie", 1)]


def test_count_by_group_with_where():
    """count_by_group applies WHERE filter."""
    conn = MagicMock()
    conn.execute.return_value.fetchall.return_value = []

    query.count_by_group(conn, "tasks", "agent_id", where="status = 'done'")
    call_args = conn.execute.call_args[0][0]
    assert "WHERE status = 'done'" in call_args
    assert "GROUP BY agent_id" in call_args


def test_count_by_group_with_limit():
    """count_by_group applies LIMIT."""
    conn = MagicMock()
    conn.execute.return_value.fetchall.return_value = []

    query.count_by_group(conn, "tasks", "agent_id", limit=5)
    call_args = conn.execute.call_args[0][0]
    assert "LIMIT ?" in call_args
    assert conn.execute.call_args[0][1] == (5,)


def test_update_where():
    """update_where executes UPDATE with parameterized values."""
    conn = MagicMock()

    query.update_where(
        conn, "agents", {"name": "alice", "status": "active"}, "agent_id = ?", ("id-1",)
    )

    call_args = conn.execute.call_args[0]
    qry = call_args[0]
    params = call_args[1]

    assert "UPDATE agents SET" in qry
    assert "name = ?" in qry
    assert "status = ?" in qry
    assert "WHERE agent_id = ?" in qry
    assert params == ("alice", "active", "id-1")


def test_update_where_empty_updates():
    """update_where does nothing if updates dict is empty."""
    conn = MagicMock()

    query.update_where(conn, "agents", {}, "agent_id = ?", ("id-1",))
    conn.execute.assert_not_called()


def test_delete_where():
    """delete_where executes DELETE with parameterized values."""
    conn = MagicMock()

    query.delete_where(conn, "agents", "agent_id = ?", ("id-1",))

    call_args = conn.execute.call_args[0]
    qry = call_args[0]
    params = call_args[1]

    assert "DELETE FROM agents" in qry
    assert "WHERE agent_id = ?" in qry
    assert params == ("id-1",)
