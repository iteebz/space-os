# The App Model: The Core of Application Development

This document outlines the definitive `App` model in the `agent-space` architecture, serving as the foundation for all applications.

## The `App` Class: The Foundation

The `space/os/core/app.py` file defines the `App` class. This class is the core abstraction for all applications running within the `agent-space` OS. All applications in `space/apps/` **must** inherit from this `App` class.

### Benefits of the `App` Class

*   **Default Implementations:** The `App` class provides default implementations for common app functionalities, significantly reducing boilerplate code in each application.
*   **Shared Functionality:** It centralizes shared functionality directly into the "OS" level, such as:
    *   Automated database path management (`db_path`).
    *   Standardized hooks for initialization (`initialize()`).
    *   A consistent way to define the CLI group (`cli_group()`).
*   **Stronger Contract:** A base class provides a robust contract, enforcing implementation details and providing concrete methods that all apps must adhere to or override.
*   **Simplified App Creation:** Creating a new app is streamlined to inheriting from `App` and overriding specific methods.
*   **Abstracted Data Access:** The `App` class provides a generic mechanism for apps to interact with their data stores via a repository pattern, abstracting away low-level database concerns.

### The `App` Class Definition

Here is the definition of the `App` class in `space/os/core/app.py`:

```python
# space/os/core/app.py

import click
from pathlib import Path
import sqlite3
from collections.abc import Iterator, Callable
from contextlib import contextmanager

from space.os.lib import fs
from space.os.core.storage import Storage # Import the Storage base class

# SPACE_DIR is the root directory for all application-specific data,
# typically located at the project root's .space directory.
# fs.root() resolves to the project's absolute root path.
SPACE_DIR = fs.root() / ".space"

class App:
    """
    The base class for all applications in the agent-space OS.
    """
    def __init__(self, name: str):
        self._name = name
        self._db_path = SPACE_DIR / name
        self._db_path.parent.mkdir(parents=True, exist_ok=True)
        self._repositories = {} # New: To store repository instances

    @contextmanager
    def get_db_connection(self, row_factory: type | None = None) -> Iterator[sqlite3.Connection]:
        """Yield a connection to the app's dedicated database."""
        conn = sqlite3.connect(self.db_path)
        if row_factory is not None:
            conn.row_factory = row_factory
        try:
            yield conn
        finally:
            conn.close()

    def ensure_db(self, initializer: Callable[[sqlite3.Connection], None] | None = None):
        """Create database if missing and run optional initializer inside a transaction."""
        with sqlite3.connect(self.db_path) as conn:
            if initializer is not None:
                initializer(conn)
            conn.commit()

    @property
    def name(self) -> str:
        """The unique name of the application."""
        return self._name

    @property
    def db_path(self) -> Path:
        """The path to the application's dedicated database."""
        return self._db_path

    def cli_group(self) -> click.Group:
        """
        The click command group for this application.
        This should be implemented by the subclass.
        """
        raise NotImplementedError

    def initialize(self):
        """
        A hook for the app to perform any necessary initialization,
        such as creating database schemas.
        This can be overridden by the subclass.
        """
        self.ensure_db()

    # New: Method to register and get repositories
    def register_repository(self, name: str, repo_class: type[Storage]):
        """Registers a repository class for this app."""
        self._repositories[name] = repo_class(self.db_path)

    @property
    def repositories(self):
        """Provides access to registered repository instances."""
        return self._repositories
```

### How Applications Use the `App` Class

An application's `app.py` file (e.g., `space/apps/memory/app.py`) will define a class that inherits from `App`. This class will then be instantiated and exposed as the app's entry point.

Here's an example for the `memory` app:

```python
# space/apps/memory/app.py

from space.os.core.app import App
from .cli import memory_group
from .db import ensure_schema
from .repository import MemoryRepository # New import

class Memory(App):
    def __init__(self):
        super().__init__("memory")
        self.register_repository("memory", MemoryRepository) # New line

    def cli_group(self):
        return memory_group

    def initialize(self):
        self.ensure_db(ensure_schema)

# Instantiate the app
memory_app = Memory()
```

This approach makes the app's definition clear, concise, and fully integrated with the `agent-space` OS.

## The App Pattern in Practice

Every major application in the `space` project **must** follow this structure. The `space.apps.memory` app is a canonical example:

### Directory Structure

```
space/
└── apps/                       # The Application Layer
    └── memory/                 # A self-contained 'memory' app
        ├── __init__.py         # Exposes the app's external API.
        ├── app.py              # Defines the App class for this application.
        ├── api.py              # Defines the stable, public API for OTHER apps.
        ├── cli.py              # The CLI for THIS app.
        ├── db.py               # Internal: Handles all raw database operations.
        └── memory.py           # Internal: Core business logic for "memory".
```

### The Role of Each File within an App

1.  **Internal Logic (`memory.py`):**
    *   This file contains the core business logic for the app, utilizing the app's registered repositories.
    *   It contains the detailed implementation—the "how."
    *   It is considered **private** to the app.
    *   **It must never be imported by any file outside of its own app directory.**

2.  **Repository (`repository.py`):
    *   This file encapsulates data access logic for specific entities (e.g., `MemoryRepository` for `Memory` objects).
    *   It inherits from `space.os.core.storage.Storage`, leveraging the OS-provided storage abstraction.
    *   It is considered **private** to the app.
    *   **It must never be imported by any file outside of its own app directory.**

3.  **Database Migrations (`db.py`):
    *   This file primarily handles database schema migrations and the `ensure_schema` function.
    *   It is considered **private** to the app.
    *   **It must never be imported by any file outside of its own app directory.**

4.  **The App's Own CLI (`cli.py`):**
    *   This file contains all `click` commands related to the app.
    *   As it is *part of the app*, it is a **privileged consumer**. It is allowed to import directly from its sibling files (`memory.py`, `db.py`).
    *   **Example Imports in `memory/cli.py`:**
        ```python
        from . import memory           # Direct access to internal logic
        from ...os.lib import fs       # Relative import for shared OS utilities
        ```
    *   It must define a single `click.Group` (e.g., `memory_group`) that the main application can discover and register.

3.  **The External API (`api.py`):**
    *   This file defines the stable, public-facing API that **other apps** can use to interact with this one.
    *   It provides a controlled, decoupled entry point for cross-app communication.
    *   The API exposed here may be a subset of the app's total functionality.

4.  **The Package Initializer (`__init__.py`):**
    *   This file is the **true public API gatekeeper** for the app. It defines what is exposed when other parts of the `space` application import the app.
    *   It should explicitly import specific, high-level functions from `api.py` and define an `__all__` list.
    *   It will import the instantiated `App` class (e.g., `memory_app`) from `app.py` and expose it.

## Agent Lifecycle: Implicit Registration

To simplify agent creation and ensure system-wide provenance, we use an **implicit registration** pattern.

*   **`space.apps.spawn`:** This app is the designated interface for *humans* to create and manage agent lifecycles (e.g., `space spawn <agent_name>`).
*   **`space.apps.register`:** This app is the authoritative source of truth for all agents known to the system. It manages agent metadata and their "constitutions" (guides).

When an agent is created via the `spawn` app, the `spawn` app *automatically* calls the `register` app's API to register the new agent and its constitution. The agent itself does not need to know how to register. This is analogous to an OS managing its processes.

## Constitutions (Protocols)

Constitutions (or protocols) are documents that define an agent's or app's behavior and purpose.

*   **Centralized Management:** All protocol management logic is centralized within the `space.apps.register` app.
*   **Location:** Protocols are co-located with the app they belong to (e.g., `space/apps/memory/prompts/protocol.md`). General or system-wide protocols (like `onboarding.md`) reside in `space/apps/register/prompts/`).
*   **Provenance:** The `register` app is responsible for tracking the constitutional history of each agent, providing a clear audit trail.

## Conclusion

The `App` class provides a powerful and elegant mechanism for building modular, extensible, and consistent applications within the `agent-space` ecosystem. It embodies the principle of "freedom through structure," allowing developers to focus on application logic while the OS handles foundational concerns.
