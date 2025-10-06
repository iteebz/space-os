from space.os.core.app import App
from .cli import backup_group

class Backup(App):
    def __init__(self):
        super().__init__("backup")

    def cli_group(self):
        return backup_group

    def initialize(self):
        # No specific database initialization needed for a simple backup app
        pass

backup_app = Backup()
