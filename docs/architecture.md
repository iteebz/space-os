# Architecture: The Self-Contained Module Pattern

This document codifies the definitive architectural pattern for the `space` application. This pattern is law. Adhering to it is crucial for maintaining a clean, scalable, and truly modular codebase.

## The Core Principle: True Modularity

A module (e.g., `space.apps.context`, `space.apps.registry`) must be a **completely self-contained component**. It encapsulates its own core logic, data persistence, and even its own user interface (CLI). 

This creates a "plug-and-play" architecture. To add a major feature to the application, one creates a new module directory within `space/apps/`. To remove it, one deletes the directory. The main application dynamically adapts.

## The Pattern in Practice

Every major module in the `space` project **must** follow this structure. The `space.apps.context` module is the canonical example:

### Directory Structure

```
space/
└── apps/
    └── context/                    # The self-contained 'context' module
        ├── __init__.py           # Exposes the module's external API from core.py.
        ├── core.py               # Defines the stable, public API for OTHER modules.
        ├── cli.py                # <-- The CLI for THIS module.
        ├── db.py                 # Internal: Handles all raw database operations.
        ├── memory.py             # Internal: Business logic for "memory".
        └── knowledge.py          # Internal: Business logic for "knowledge".
```

### The Role of Each File

1.  **Internal Logic (`db.py`, `memory.py`, `knowledge.py`):**
    *   These files contain the detailed implementation—the "how."
    *   They are considered **private** to the module.
    *   **They must never be imported by any file outside of their own module directory.**

2.  **The Module's Own CLI (`cli.py`):**
    *   This file contains all `click` commands related to the module.
    *   As it is *part of the module*, it is a **privileged consumer**. It is allowed to import directly from its sibling files (`memory.py`, `knowledge.py`, `db.py`).
    *   This allows for natural, intuitive, and semantic syntax within the CLI code (e.g., `memory.recall()`, `knowledge.query(domain)`).
    *   **Example Imports in `context/cli.py`:**
        ```python
        from . import memory, knowledge # Direct access to internal logic
        from ..lib import fs           # Relative import for shared utilities
        ```
    *   It must define a single `click.Group` (e.g., `context_group`) that the main application can discover and register.

3.  **The External API (`core.py`):**
    *   This file defines the stable, public-facing API that **other modules** can use to interact with this one.
    *   It provides a controlled, decoupled entry point for cross-module communication.
    *   The API exposed here may be a subset of the module's total functionality, or it may be flattened for simplicity. While the module's own `cli.py` can use highly semantic internal calls (e.g., `memory.recall()`), `core.py` might expose more explicit names for external consumers (e.g., `get_memory_entries()`) to avoid ambiguity when used outside the module's immediate context.

4.  **The Package Initializer (`__init__.py`):**
    *   This file has one job: to expose the external API defined in `core.py` to other modules.
    *   It should contain only this line: `from .core import *`

### The Main Application (`app.py`)

The main application entry point (e.g., a future `app.py` or `cli/main.py`) is now just a thin orchestrator. Its primary job is to:

1.  Discover all modules within the `space.apps` package.
2.  Import the `click.Group` from each module's `cli.py`.
3.  Register those groups into the main application CLI.

This design ensures the main application knows nothing about the internal workings of any module; it only knows how to register them.

### Why This Pattern is Law

-   **Maximum Cohesion:** Everything related to a feature (logic, data, UI) lives in a single, dedicated directory.
-   **Minimum Coupling:** Modules interact only through well-defined, stable `core.py` APIs, not by reaching into each other's internal files.
-   **Scalability:** The system scales by adding or removing entire module directories within `space/apps/`. The application automatically adapts.
-   **Developer Sanity:** This structure is predictable and easy to navigate. If you need to work on the `context` CLI, you go to `apps/context/cli.py`. If you need to see how `context` interacts with other modules, you look at `apps/context/core.py`.
