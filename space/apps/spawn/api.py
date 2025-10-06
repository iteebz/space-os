from space.apps.register import api as register_api

def spawn(
    agent_id: str,
    role: str,
    channels: list[str],
    constitution_hash: str,
    provider: str | None,
    model: str | None,
):
    """
    Spawns an agent and implicitly registers it with the system.
    """
    # Here, you would have the logic to actually "spawn" the agent,
    # e.g., by creating a new process, a Docker container, or a Kubernetes pod.
    # For now, we will just simulate this by printing a message.
    print(f"Spawning agent '{agent_id}'...")

    # After spawning, implicitly register the agent.
    # We need to get the constitution content from the hash.
    constitution_content = register_api.get_constitution_content(constitution_hash)
    if not constitution_content:
        raise ValueError(f"Constitution with hash '{constitution_hash}' not found.")

    register_api.link(
        agent_id=agent_id,
        role=role,
        channels=channels,
        constitution_hash=constitution_hash,
        constitution_content=constitution_content,
        provider=provider,
        model=model,
    )