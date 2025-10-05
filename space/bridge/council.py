import random
from pathlib import Path

from rich.text import Text
from textual.app import App, ComposeResult
from textual.containers import Vertical
from textual.message import Message
from textual.widgets import Header, Input, RichLog

from . import coordination, storage


class SendMsg(Message):
    def __init__(self, content: str) -> None:
        super().__init__()
        self.content = content


class Council(App):
    CSS = """
    Screen {
        background: #0a0a0a;
    }
    Header {
        background: #0a0a0a;
        color: #666;
        border-bottom: tall #1a1a1a;
        height: 1;
    }
    Footer {
        display: none;
    }
    #log {
        height: 1fr;
        background: #0a0a0a;
        border: none;
        padding: 0 2;
        scrollbar-size: 1 1;
    }
    #log:focus {
        border: none;
    }
    #input {
        dock: bottom;
        height: 3;
        background: #0a0a0a;
        border: none;
        border-top: tall #1a1a1a;
        padding: 0 2;
    }
    #input:focus {
        border-top: tall #1a1a1a;
    }
    Input {
        background: #0a0a0a;
        color: #ccc;
    }
    """

    BINDINGS = [
        ("ctrl+d", "quit", "Quit"),
    ]

    def __init__(self, channel: str, identity: str):
        super().__init__()
        self.channel = channel
        self.channel_id = coordination.resolve_channel_id(channel)
        self.identity = identity
        self.spoken = set()
        self.identity_colors = {}
        self.draft_path = Path.home() / ".space" / "drafts" / f"{channel}.txt"

    def compose(self) -> ComposeResult:
        yield Header()
        with Vertical():
            yield RichLog(id="log", wrap=True, markup=True)
            yield Input(id="input", placeholder="")

    def on_mount(self) -> None:
        self.spoken.clear()
        self.set_interval(1, self.poll)
        self.title = self.channel

        log = self.query_one("#log", RichLog)
        log.write(f"[dim]→ {self.channel}[/dim]\n")

        msgs = coordination.fetch_messages(self.channel_id)
        if msgs:
            for m in msgs:
                log.write(self._fmt(m.sender, m.content))
            log.write("")
            storage.set_bookmark(self.identity, self.channel_id, msgs[-1].id)

        inp = self.query_one("#input", Input)
        if self.draft_path.exists():
            inp.value = self.draft_path.read_text()
        inp.focus()

    async def poll(self) -> None:
        msgs, unread, _, _ = coordination.recv_updates(self.channel_id, self.identity)
        if unread > 0:
            log = self.query_one("#log", RichLog)
            for m in msgs:
                if m.sender != self.identity:
                    self.spoken.add(m.sender)
                    log.write(self._fmt(m.sender, m.content))

    def on_input_changed(self, event: Input.Changed) -> None:
        if event.value:
            self._save_draft(event.value)
        else:
            self._clear_draft()

    def on_input_submitted(self, event: Input.Submitted) -> None:
        msg = event.value.strip()
        if not msg:
            return

        inp = self.query_one("#input", Input)
        log = self.query_one("#log", RichLog)

        if msg == "!done":
            self.spoken.add(self.identity)
            if len(self.spoken) < 2:
                log.write("[dim red]need 2+ speakers[/dim red]\n")
                inp.value = ""
                self._clear_draft()
                return
            log.write("[dim green]✓[/dim green]")
            self._clear_draft()
            self.exit()
            return

        try:
            coordination.send_message(self.channel_id, self.identity, msg)
            self.spoken.add(self.identity)
            log.write(self._fmt(self.identity, msg))
            inp.value = ""
            self._clear_draft()
        except Exception as e:
            log.write(f"[red]Error: {e}[/red]\n")
            self._save_draft(msg)

    def _save_draft(self, content: str) -> None:
        self.draft_path.parent.mkdir(parents=True, exist_ok=True)
        self.draft_path.write_text(content)

    def _clear_draft(self) -> None:
        if self.draft_path.exists():
            self.draft_path.unlink()

    def _fmt(self, sender: str, content: str) -> Text:
        if sender not in self.identity_colors:
            if sender == self.identity:
                self.identity_colors[sender] = "magenta"
            else:
                self.identity_colors[sender] = random.choice(
                    [
                        "red",
                        "green",
                        "yellow",
                        "blue",
                        "cyan",
                        "bright_red",
                        "bright_green",
                        "bright_yellow",
                        "bright_blue",
                        "bright_cyan",
                    ]
                )
        color = self.identity_colors[sender]
        return Text.from_markup(f"[{color}]{sender}[/{color}]: {content}\n")


if __name__ == "__main__":
    Council(channel="test", identity="detective").run()
