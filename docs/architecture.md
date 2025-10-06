# Architecture: The OS/App Model

This document codifies the definitive architectural pattern for the `space` application. This pattern is law. Adhering to it is crucial for maintaining a clean, scalable, and truly modular codebase.

## The Core Principle: A Clear OS/App Separation

The `space` architecture is modeled after a traditional operating system, with a clear separation between the core **Operating System (`os`)** layer and the **Applications (`apps`)** that run on top of it.

*   **The OS Layer:** Provides a stable, application-agnostic platform with core services. It is the "kernel" of our "OS for agents." For detailed information, refer to [os.md](os.md).
*   **The Application Layer:** Contains self-contained modules, each focused on a specific domain. For detailed information, refer to [apps.md](apps.md).

This creates a "plug-and-play" architecture. To add a major feature, one creates a new app directory within `space/apps/`. To remove it, one deletes the directory. The main application dynamically adapts.

## The Main Application (`space/cli.py`)

The main application entry point is a thin orchestrator. Its primary job is to:

1.  Discover all apps within the `space.apps` package.
2.  Instantiate the `App` class from each app's `app.py` file.
3.  Register the `cli_group` from each instantiated app into the main application CLI.

This design ensures the main application knows nothing about the internal workings of any app.

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

### Why This Pattern is Law

-   **Maximum Cohesion:** Everything related to a feature lives in a single, dedicated app directory.
-   **Minimum Coupling:** Apps interact only through well-defined, stable `api.py` APIs, not by reaching into each other's internal files.
-   **Clear Separation of Concerns:** The `os/` layer is cleanly separated from the `apps/` layer, with a one-way dependency (`apps` depend on `os`).
-   **Scalability:** The system scales by adding or removing entire app directories.
-   **Developer Sanity:** This structure is predictable and easy to navigate.

## Styling and Naming Conventions

These conventions are not merely stylistic preferences; they are crucial for maintaining architectural clarity, reducing cognitive load, and ensuring consistency across a modular system. Adhering to these guidelines is paramount for readability and maintainability.

*   **Internal Modules:** Use plural nouns for internal modules that represent collections or domains (e.g., `channels.py`, `messages.py`).
*   **Function Naming:** Prefer short, clear verbs. The module name provides context, so avoid redundancy (e.g., `channels.create()`, `messages.send()`).
*   **API Naming:** Use clear, unambiguous aliases in `api.py` to prevent name collisions and provide context for external consumers (e.g., `from .memory import recall as get_memory_entries`).
