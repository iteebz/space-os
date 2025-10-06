# The OS Layer: Core Services for Agent-Space

This document details the `os/` layer of the `agent-space` architecture, which serves as the foundational operating system for all applications.

## The Core Principle: A Stable Platform

The `os/` layer provides a stable, application-agnostic platform with core services. It is the "kernel" and "system services" of our "OS for agents," offering essential functionalities that applications rely upon.

## Directory Structure

```
space/
└── os/                         # The Operating System Layer
    ├── core/                   # Fundamental, cross-cutting components (e.g., app.py)
    ├── db/                     # Database-related OS services (e.g., migrations.py)
    ├── events/                 # System-wide eventing mechanism
    ├── lib/                    # Shared libraries and utilities
    ├── config.py               # System-wide configuration settings
    └── stats.py                # System-level statistics service
```

## The Role of Each Component

1.  **`os/core/`:
    *   **Purpose:** Reserved for fundamental, cross-cutting components that are essential to the `space` ecosystem and designed for reuse across multiple applications. This includes `app.py`, which defines the foundational `App` class. These components represent core domain services, distinct from general-purpose utilities.

2.  **`os/db/`:**
    *   **Purpose:** Contains database-related OS services, such as `migrations.py` for managing all schema evolution across applications. This centralizes migration logic, ensuring consistency and reducing complexity in individual apps.

3.  **`os/events/`:
    *   **Purpose:** Contains the system-wide eventing mechanism (e.g., `events.py`). Applications emit events through this service, and the system can track and react to them.

4.  **`os/lib/`:
    *   **Purpose:** Contains shared libraries and utilities (e.g., `fs` for filesystem operations, `sha256` for hashing, `uuid7` for UUID generation). These are the equivalent of system libraries in a traditional OS.

5.  **`os/config.py`:
    *   **Purpose:** Contains system-wide configuration settings, analogous to system configuration files in a traditional OS.

6.  **`os/stats.py`:
    *   **Purpose:** Collects and reports statistics across different applications. This is a system-level service that provides an overview of the entire `agent-space` environment.

## Relationship with Applications

*   **One-Way Dependency:** The `apps/` layer depends on the `os/` layer, but the `os/` layer does not depend on the `apps/` layer. This is a crucial architectural principle that ensures a clean separation of concerns.
*   **Services for Apps:** The `os/` layer provides essential services that applications consume, allowing apps to focus on their domain-specific logic without managing low-level system concerns.