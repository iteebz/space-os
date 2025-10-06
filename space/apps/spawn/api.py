from space.apps.registry import api as registry_api
from space.os.lib import sha256 # Import sha256 for hashing
from typing import Optional

def spawn(
    agent_id: str,
    role: str,
    channels: list[str],
    constitution_content: str, # Now accepts content directly
    provider: Optional[str] = None,
    model: Optional[str] = None,
):
    """
    Spawns an agent and implicitly registers it with the system.
    """
    # Here, you would have the logic to actually "spawn" the agent,
    # e.g., by creating a new process, a Docker container, or a Kubernetes pod.
    # For now, we will just simulate this by printing a message.
    print(f"Spawning agent '{agent_id}' with role '{role}'...")

    # Calculate the hash of the constitution content
    constitution_hash = sha256.sha256(constitution_content)

    # Register the constitution version with the registry
    constitution = registry_api.add_constitution_version(
        name=f"{agent_id}_constitution", # A name for this constitution version
        content=constitution_content,
        identity_id=agent_id, # Link to the agent being spawned
        change_description="Initial constitution during agent spawn",
        created_by="spawn_app",
    )
    print(f"Constitution version registered with hash: {constitution.hash}")

    # Register the agent identity with the registry, linking to the constitution hash
    identity = registry_api.add_identity(
        id=agent_id,
        type=role, # Using role as the identity type
        initial_constitution_hash=constitution_hash, # Link to the registered constitution
    )
    print(f"Agent '{agent_id}' registered with ID: {identity.id}")

    # Further logic for channels, provider, model can be added here if needed
    # For example, linking channels to the identity in the registry or another app