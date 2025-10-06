# Architecture: The OS/App Model

This document codifies the definitive architectural pattern for the `space` application. This pattern is law. Adhering to it is crucial for maintaining a clean, scalable, and truly modular codebase.

## The Core Principle: A Clear OS/App Separation

The `space` architecture is modeled after a traditional operating system, with a clear separation between the core **Operating System (`os`)** layer and the **Applications (`apps`)** that run on top of it.

*   **`space/os/`:** The OS layer provides a stable, application-agnostic platform with core services (eventing, libraries, protocols). It is the "kernel" of our "OS for agents."
*   **`space/apps/`:** The Application layer contains self-contained modules, each focused on a specific domain (e.g., `bridge`, `memory`, `spawn`).

This creates a "plug-and-play" architecture. To add a major feature, one creates a new app directory within `space/apps/`. To remove it, one deletes the directory. The main application dynamically adapts.

## The App Pattern in Practice

Every major application in the `space` project **must** follow this structure. The `space.apps.memory` app is a canonical example:

### Directory Structure

```
space/
├── os/                         # The Operating System Layer
│   ├── events/
│   ├── lib/
│   └── protocols.py
└── apps/                       # The Application Layer
    └── memory/                 # A self-contained 'memory' app
        ├── __init__.py         # Exposes the app's external API.
        ├── api.py              # Defines the stable, public API for OTHER apps.
        ├── cli.py              # The CLI for THIS app.
        ├── db.py               # Internal: Handles all raw database operations.
        └── memory.py           # Internal: Core business logic for "memory".
```

### The Role of Each File

1.  **Internal Logic (`db.py`, `memory.py`):**
    *   These files contain the detailed implementation—the "how."
    *   They are considered **private** to the app.
    *   **They must never be imported by any file outside of their own app directory.**

2.  **The App's Own CLI (`cli.py`):**
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
    *   **Protocol Conformance:** It explicitly declares conformance to the `App` protocol, providing the app's `name` and its `cli_group` for dynamic discovery.

### The App Protocol (`space/os/protocols.py`)

To enforce architectural consistency, all app modules **must** conform to the `App` protocol defined in `space/os/protocols.py`. This protocol requires each app to provide:

*   **`name` (property):** A unique string name (e.g., "memory").
*   **`cli_group()` (method):** A `click.Group` object for its CLI commands.

Conformance is declared in the app's `__init__.py` file using `typing.cast(App, sys.modules[__name__])`.

### The Main Application (`space/cli.py`)

The main application entry point is a thin orchestrator. Its primary job is to:

1.  Discover all apps within the `space.apps` package.
2.  Import the `click.Group` from each app.
3.  Register those groups into the main application CLI.

This design ensures the main application knows nothing about the internal workings of any app.

## Agent Lifecycle: Implicit Registration

To simplify agent creation and ensure system-wide provenance, we use an **implicit registration** pattern.

*   **`space.apps.spawn`:** This app is the designated interface for *humans* to create and manage agent lifecycles (e.g., `space spawn <agent_name>`).
*   **`space.apps.register`:** This app is the authoritative source of truth for all agents known to the system. It manages agent metadata and their "constitutions" (guides).

When an agent is created via the `spawn` app, the `spawn` app *automatically* calls the `register` app's API to register the new agent and its constitution. The agent itself does not need to know how to register. This is analogous to an OS managing its processes.

## Constitutions (Guides)

Constitutions (or guides) are documents that define an agent's or app's behavior and purpose.

*   **Centralized Management:** All guide management logic is centralized within the `space.apps.register` app.
*   **Location:** Guides are co-located with the app they belong to (e.g., `space/apps/memory/prompts/guides/memory.md`). General or system-wide guides (like `onboarding.md`) reside in `space/apps/register/prompts/guides/`.
*   **Provenance:** The `register` app is responsible for tracking the constitutional history of each agent, providing a clear audit trail.

### Why This Pattern is Law

-   **Maximum Cohesion:** Everything related to a feature lives in a single, dedicated app directory.
-   **Minimum Coupling:** Apps interact only through well-defined, stable `api.py` APIs, not by reaching into each other's internal files.
-   **Clear Separation of Concerns:** The `os/` layer is cleanly separated from the `apps/` layer, with a one-way dependency (`apps` depend on `os`).
-   **Scalability:** The system scales by adding or removing entire app directories.
-   **Developer Sanity:** This structure is predictable and easy to navigate.

## Styling and Naming Conventions

*   **Internal Modules:** Use plural nouns for internal modules that represent collections or domains (e.g., `channels.py`, `messages.py`).
*   **Function Naming:** Prefer short, clear verbs. The module name provides context, so avoid redundancy (e.g., `channels.create()`, `messages.send()`).
*   **API Naming:** Use clear, unambiguous aliases in `api.py` to prevent name collisions and provide context for external consumers (e.g., `from .memory import recall as get_memory_entries`).