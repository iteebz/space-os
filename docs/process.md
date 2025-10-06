# Radical Refactoring Process: Reference-Grade TDD

This document outlines the process for performing a radical refactoring of a core application component, aiming to achieve a "reference-grade" implementation driven by Test-Driven Development (TDD) and strict adherence to the architectural principles defined in `architecture.md`.

## Objective

To deeply understand a specific application area, rebuild it with meticulous TDD, and ensure it perfectly embodies the architectural "law" of the `space` application, serving as a blueprint for future development and refactoring efforts.

## Chosen Area for Initial Refactoring: The `memory` App

The `memory` app (`private/agent-space/space/apps/memory`) has been selected as the initial focus due to its role as a canonical example in the `architecture.md` document. This allows for direct validation against the established architectural principles.

## Process Steps

1.  **Deep Understanding of the Target App's Role:**
    *   **Action:** Re-read `private/agent-space/docs/architecture.md` with a specific focus on the chosen app (`memory`), its defined responsibilities, and the expected interactions of its components (`api.py`, `cli.py`, `__init__.py`, `db.py`, `memory.py`).
    *   **Goal:** Internalize the architectural "law" as it applies to this specific app, identifying all explicit and implicit constraints and expectations.

2.  **Define API Contract via Comprehensive TDD:**
    *   **Action:** Begin by writing a comprehensive suite of unit tests for the `memory` app's public API, as exposed through `api.py`. These tests will be written *before* any implementation changes.
    *   **Considerations:**
        *   Tests should cover all expected functionalities and edge cases of the `api.py` functions.
        *   Tests should validate adherence to architectural principles (e.g., ensuring no direct internal imports from other apps, proper data flow).
        *   Tests should define the *desired* behavior, not necessarily the *current* broken behavior.
    *   **Goal:** Establish a robust, executable contract for the `memory` app's external interface, ensuring it aligns with the architectural vision. These tests will initially fail.

3.  **Incremental Refactoring and Implementation (Red-Green-Refactor Cycle):**
    *   **Action:** Work through the `memory` app's components (`db.py`, `memory.py`, `cli.py`, `__init__.py`, and any other relevant files like `models.py` or `prompts/`) in small, manageable steps.
    *   **Methodology:** Apply the Red-Green-Refactor cycle:
        *   **Red:** Write a small test that fails (or ensures an existing test fails for a specific new behavior).
        *   **Green:** Write *just enough* code to make the test pass. Focus solely on functionality.
        *   **Refactor:** Improve the code's design, readability, and adherence to architectural principles, ensuring all tests remain green.
    *   **Focus:** Strictly adhere to the architectural guidelines from `architecture.md`, including encapsulation, clear separation of concerns, proper protocol conformance (in `__init__.py`), and naming conventions.
    *   **Goal:** Rebuild the `memory` app to be a "reference-grade" implementation that is fully tested, architecturally compliant, and highly maintainable.

4.  **Integration and Verification:**
    *   **Action:** Once the `memory` app's internal tests are passing and the implementation is deemed "reference-grade," integrate it back into the broader `space` application.
    *   **Goal:** Ensure the refactored app functions correctly within the larger system and that its public API is consumed as expected by other components.

## Guiding Principles

*   **TDD First:** All new or refactored code will be driven by tests.
*   **Architectural Law:** Strict adherence to `architecture.md` is paramount.
*   **Incremental Changes:** Break down the refactoring into the smallest possible steps.
*   **Quality Over Speed:** Focus on building a high-quality, maintainable, and correct solution.
*   **Documentation:** Update relevant documentation (including `architecture.md` if necessary for clarifications) as the refactoring progresses.
