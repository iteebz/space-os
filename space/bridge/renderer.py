import sys
import signal
from typing import Iterator
from dataclasses import dataclass

@dataclass
class Event:
    type: str  # 'token' | 'status' | 'error' | 'done'
    content: str = ""

class Renderer:
    def __init__(self):
        self._status_active = False
        signal.signal(signal.SIGINT, self._cleanup)
    
    def render(self, events: Iterator[Event]):
        try:
            for event in events:
                if event.type == 'token':
                    self._clear_status()
                    sys.stdout.write(event.content)
                    sys.stdout.flush()
                
                elif event.type == 'status':
                    self._show_status(event.content)
                
                elif event.type == 'error':
                    self._clear_status()
                    sys.stderr.write(f"\nError: {event.content}\n")
                
                elif event.type == 'done':
                    self._clear_status()
                    sys.stdout.write('\n')
        
        finally:
            self._clear_status()
    
    def _show_status(self, msg: str):
        # Overwrite current line
        sys.stdout.write(f"\r{msg}")
        sys.stdout.flush()
        self._status_active = True
    
    def _clear_status(self):
        if self._status_active:
            # Clear line completely
            sys.stdout.write('\r' + ' ' * 80 + '\r')
            sys.stdout.flush()
            self._status_active = False
    
    def _cleanup(self, signum, frame):
        self._clear_status()
        sys.exit(0)