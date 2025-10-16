from unittest.mock import patch

import pytest
import typer

from space.memory.app import main


def test_main_zero_exit_propagates(test_space):
    """main() exits with code 0 on success."""
    with patch("space.memory.app.app") as mock_app:
        mock_app.side_effect = typer.Exit(code=0)

        with pytest.raises(SystemExit) as exc_info:
            main()

        assert exc_info.value.code == 0


def test_main_error_exit_emits_event(test_space):
    """main() emits error event on non-zero exit."""
    from space import events

    with patch("space.memory.app.app") as mock_app:
        mock_app.side_effect = typer.Exit(code=1)

        with pytest.raises(SystemExit) as exc_info:
            main()

        assert exc_info.value.code == 1
        emitted = events.query(source="cli")
        assert any(e.event_type == "error" for e in emitted)


def test_main_exception_emits_error_event(test_space):
    """main() emits error event and exits 1 on exception."""
    from space import events

    with patch("space.memory.app.app") as mock_app:
        mock_app.side_effect = ValueError("test error")

        with pytest.raises(SystemExit) as exc_info:
            main()

        assert exc_info.value.code == 1
        emitted = events.query(source="cli")
        assert any(e.event_type == "error" for e in emitted)
        assert any("test error" in e.data for e in emitted if e.data)


def test_main_exception_no_traceback(test_space, capsys):
    """main() does not print traceback for exceptions."""
    with patch("space.memory.app.app") as mock_app:
        mock_app.side_effect = RuntimeError("internal error")

        with pytest.raises(SystemExit):
            main()

        captured = capsys.readouterr()
        assert "Traceback" not in captured.err
