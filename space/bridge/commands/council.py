"""Live bridge council - stream messages + type freely."""

import asyncio
import sys
from collections import deque
from datetime import datetime

import typer
from prompt_toolkit import PromptSession
from prompt_toolkit.history import InMemoryHistory
from prompt_toolkit.patch_stdout import patch_stdout

from space.spawn import registry

from .. import api, db


class Council:
    def __init__(self, channel_name: str):
        self.channel_name = channel_name
        self.channel_id = api.channels.resolve_channel_id(channel_name)
        self.last_msg_id = None
        self.running = True
        self._lock = asyncio.Lock()
        self.sent_msg_ids = set()
        self.message_queue = deque(maxlen=100)
        self.session = PromptSession(history=InMemoryHistory())

    async def stream_messages(self):
        """Stream new messages from channel."""
        while self.running:
            try:
                msgs = db.get_all_messages(self.channel_id)
                if msgs:
                    start_idx = 0
                    if self.last_msg_id:
                        for i, msg in enumerate(msgs):
                            if msg.message_id == self.last_msg_id:
                                start_idx = i + 1
                                break

                    for msg in msgs[start_idx:]:
                        if msg.message_id not in self.sent_msg_ids:
                            async with self._lock:
                                self._print_message(msg)
                        self.last_msg_id = msg.message_id

                await asyncio.sleep(0.5)
            except Exception as e:
                async with self._lock:
                    self._print_error(f"Stream error: {e}")
                await asyncio.sleep(1)

    async def read_input(self):
        """Read user input asynchronously with prompt_toolkit."""
        loop = asyncio.get_event_loop()
        while self.running:
            try:
                with patch_stdout():
                    msg = await loop.run_in_executor(None, self.session.prompt, "→ ")
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
        identity = registry.get_identity(msg.agent_id) or msg.agent_id
        ts = datetime.fromisoformat(msg.created_at).strftime("%H:%M:%S")
        prefix = "←" if identity != "human" else "→"
        print(f"{prefix} {ts} {identity}: {msg.content}")

    def _print_error(self, msg: str):
        """Print error to stderr."""
        print(f"\n⚠️  {msg}\n", file=sys.stderr)

    async def run(self):
        """Main loop - stream + input."""
        try:
            topic = db.get_topic(self.channel_id)
            print(f"\n📡 {self.channel_name}")
            if topic:
                print(f"   {topic}")
            print()

            stream_task = asyncio.create_task(self.stream_messages())
            input_task = asyncio.create_task(self.read_input())

            await asyncio.gather(stream_task, input_task)
        except KeyboardInterrupt:
            print("\n")
        finally:
            self.running = False


def council(
    channel: str = typer.Argument(..., help="Channel name"),
    identity: str = typer.Option("human", "--as", help="Identity (defaults to human)"),
):
    """Join a bridge council - stream messages and respond live."""
    c = Council(channel)
    asyncio.run(c.run())


def main() -> None:
    """Entry point."""
    typer.run(council)
