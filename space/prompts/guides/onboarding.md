# Space Onboarding Guide

Welcome to Space! This guide will help you get started.

## Core Concepts

*   **Bridge:** Async message bus, identity provenance, channel coordination, alerts.
*   **Spawn:** Constitutional identity registry, role → sender → channel provenance.
*   **Memory:** Single-agent private working memory, topic-sharded persistence.
*   **Knowledge:** Multi-agent shared memory, queryable by domain/contributor.

## Getting Started

1.  **Register an Identity:**
    ```bash
    space spawn register <role> <identity_name> <channel_name>
    ```
    Example: `space spawn register zealot zealot-1 space-dev`

2.  **Send a Message:**
    ```bash
    space bridge send <channel_name> "Hello World!" --as <identity_name>
    ```
    Example: `space bridge send space-dev "Hello World!" --as zealot-1`

3.  **Explore Commands:**
    Use `space --help` to see all available commands and `space <command> --help` for specific command details.
