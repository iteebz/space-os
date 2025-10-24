"""Live bridge council - stream messages + type freely."""

import asyncio
import sys

import typer
from prompt_toolkit import PromptSession
from prompt_toolkit.history import InMemoryHistory
from prompt_toolkit.patch_stdout import patch_stdout

from space.os.bridge import api, db

from .formatter import format_error, format_header, format_message

STREAM_POLL_INTERVAL = 0.5
STREAM_ERROR_BACKOFF = 1.0


class Council:
    def __init__(self, channel_name: str):
        self.channel_name = channel_name
        self.channel_id = api.channels.resolve_channel_id(channel_name)
        self.last_msg_id = None
        self.running = True
        self._lock = asyncio.Lock()
        self.sent_msg_ids = set()
        self.session = PromptSession(history=InMemoryHistory())
        self._last_printed_agent_id = None

    async def stream_messages(self):
        """Stream new messages from channel."""
        while self.running:
            try:
                msgs = db.get_all_messages(self.channel_id)
                if msgs:
                    start_idx = self._find_new_messages_start(msgs)
                    for msg in msgs[start_idx:]:
                        if msg.message_id not in self.sent_msg_ids:
                            async with self._lock:
                                self._print_message(msg)
                        self.last_msg_id = msg.message_id

                await asyncio.sleep(STREAM_POLL_INTERVAL)
            except Exception as e:
                async with self._lock:
                    self._print_error(f"Stream error: {e}")
                await asyncio.sleep(STREAM_ERROR_BACKOFF)

    def _find_new_messages_start(self, msgs: list) -> int:
        """Find index of first unprocessed message."""
        if not self.last_msg_id:
            return 0
        for i, msg in enumerate(msgs):
            if msg.message_id == self.last_msg_id:
                return i + 1
        return 0

    async def read_input(self):
        """Read user input asynchronously with prompt_toolkit."""
        loop = asyncio.get_event_loop()
        while self.running:
            try:
                with patch_stdout():
                    msg = await loop.run_in_executor(None, self.session.prompt, "> ")
                msg = msg.strip()
                if msg:
                    api.messages.send_message(self.channel_id, "human", msg)
                    msgs = db.get_all_messages(self.channel_id)
                    if msgs:
                        self.sent_msg_ids.add(msgs[-1].message_id)
            except EOFError:
                self.running = False
            except Exception as e:
                self._print_error(f"Input error: {e}")

    def _print_message(self, msg):
        """Print a message with identity + timestamp (safe with prompt_toolkit)."""
        agent_id = msg.agent_id
        is_user = agent_id == "human"

        if self._should_add_separator(agent_id, is_user):
            print()

        print(format_message(msg, is_user))
        self._last_printed_agent_id = agent_id

    def _should_add_separator(self, agent_id: str, is_user: bool) -> bool:
        """Determine if a blank line should precede this message."""
        if not self._last_printed_agent_id:
            return False
        if is_user:
            return False
        return self._last_printed_agent_id != agent_id

    def _print_error(self, msg: str):
        """Print error to stderr."""
        print(format_error(msg), file=sys.stderr)

    async def run(self):
        """Main loop - stream + input."""
        try:
            topic = db.get_topic(self.channel_id)
            print(format_header(self.channel_name, topic), end="")

            stream_task = asyncio.create_task(self.stream_messages())
            input_task = asyncio.create_task(self.read_input())

            await asyncio.gather(stream_task, input_task)
        except KeyboardInterrupt:
            print("\n")
        finally:
            self.running = False


def council(channel: str = typer.Argument(..., help="Channel name")):
    """Join a bridge council - stream messages and respond live."""
    c = Council(channel)
    asyncio.run(c.run())


def main() -> None:
    """Entry point."""
    typer.run(council)
