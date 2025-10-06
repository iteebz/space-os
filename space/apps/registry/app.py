from space.os.core.app import App
from space.apps.registry.repo import RegistryRepo
from .cli import registry_group # Import the cli_group

class Registry(App):
    def __init__(self):
        super().__init__("registry")
        self.register_repository("registry", RegistryRepo) # Register the repository
        from . import api
        api._set_registry_app_instance(self)

    def cli_group(self):
        """
        The click command group for this application.
        """
        return registry_group

    def initialize(self):
        self.ensure_db()
        # Explicitly call create_table on the registered repository
        self.repositories["registry"].create_table()

registry_app = Registry()