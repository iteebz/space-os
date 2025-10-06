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
        ├── api.py               # Defines the stable, public API for OTHER modules.
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
    *   This file is the **true public API gatekeeper** for the module. It defines what is exposed when other parts of the `space` application (or external consumers) import the module (e.g., `from space.apps.bridge import bridge`).
    *   It exposes a curated set of top-level functions and sub-modules to provide a clean, intuitive, and Pythonic API.
    *   **It should NOT simply contain `from .api import *`**. Instead, it should explicitly import:
        *   Specific, high-level functions from `api.py` directly into the module's namespace (e.g., `from .api import send_message, receive_messages`).
        *   Internal modules as sub-modules (e.g., `from . import channels`, `from . import messages`).
    *   It should define an `__all__` list to control what is exposed by `from module import *`.

### The Main Application (`app.py`)

The main application entry point (e.g., a future `app.py` or `cli/main.py`) is now just a thin orchestrator. Its primary job is to:

1.  Discover all modules within the `space.apps` package.
2.  Import the `click.Group` from each module's `cli.py`.
3.  Register those groups into the main application CLI.

This design ensures the main application knows nothing about the internal workings of any module; it only knows how to register them.

### Core Components (`space/core/`)

The `space/core/` directory is reserved for fundamental, cross-cutting components that are essential to the `space` ecosystem and designed for reuse across multiple applications. These components represent core domain services, distinct from general-purpose utilities found in `space/lib/`).

**Example:** `space/core/guide.py`
This module provides generic functionalities for managing application guides (e.g., loading guide content from `prompts/guides/`, hashing content, and tracking guides in the `registry` app).

### Why This Pattern is Law

-   **Maximum Cohesion:** Everything related to a feature (logic, data, UI) lives in a single, dedicated directory.
-   **Minimum Coupling:** Modules interact only through well-defined, stable `api.py` APIs, not by reaching into each other's internal files.
-   **Scalability:** The system scales by adding or removing entire module directories within `space/apps/`. The application automatically adapts.
-   **Developer Sanity:** This structure is predictable and easy to navigate. If you need to work on the `context` CLI, you go to `apps/context/cli.py`. If you need to see how `context` interacts with other modules, you look at `apps/context/api.py`.

## Styling Guides and Naming Conventions

Adhering to consistent styling and naming conventions is crucial for maintaining a readable, intuitive, and maintainable codebase.

### 1. Module and Function Naming

*   **Internal Modules:** Use plural nouns for internal modules that represent collections or domains (e.g., `channels.py`, `messages.py`, `alerts.py`, `notes.py`).
*   **Function Naming within Internal Modules:**
    *   Prefer short, clear verbs that describe the action.
    *   The module name provides context, so avoid redundancy.
    *   **Vision:** `channels.create()`, `channels.archive()`, `messages.send()`, `messages.fetch()`, `alerts.fetch()`, `notes.create()`, `notes.fetch()`. 
    *   **Avoid:** `channels.create_channel_record()`, `channels.archive_channel()`, `alerts.get_alerts()`.

### 2. Public API Exposure (`api.py` and `__init__.py`)

*   **`api.py`:** This file serves as an internal collection of all public-facing functions from internal modules. It should use clear, unambiguous aliases to prevent name collisions and provide context.
    *   **Example:** `from .channels import create as create_channel`
*   **`__init__.py`:** This file explicitly defines the module's public API.
    *   It imports specific, high-level functions from `api.py` directly into the module's namespace (e.g., `from .api import create_channel`).
    *   It imports internal modules as sub-modules (e.g., `from . import channels`).
    *   It defines an `__all__` list to control what is exposed by `from module import *`.

### 3. Guide Management Pattern

*   **Guide Content:** Guide content for each app should reside in `space/prompts/guides/{app_name}.md` (e.g., `space/prompts/guides/bridge.md`).
*   **Shared Guide Helpers:** Generic guide management utilities (loading, hashing, registry interaction) should be placed in `space/core/guide.py`.
*   **App-Specific Guide Manager:** Each app should have its own `guide_manager.py` (e.g., `bridge/guide_manager.py`) to orchestrate guide usage, load default guides, and ensure auto-registration with the `registry`.
