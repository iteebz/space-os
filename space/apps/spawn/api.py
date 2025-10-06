import json
import shlex
import subprocess
from pathlib import Path

from space import config
from space.apps import registry
from space.lib import fs, sha256


class Spawner:
    def get_constitution_path(self, role: str) -> Path:
        """Get the path to the constitution file for a given role."""
        return fs.root() / "private" / "canon" / "constitutions" / f"{role}.md"

    def _get_agent_config_from_file(self, agent_id: str) -> dict | None:
        """Load agent configuration from a JSON file if it exists."""
        agent_config_path = fs.root() / "private" / "agents" / f"{agent_id}.json"
        if agent_config_path.exists():
            return json.loads(agent_config_path.read_text())
        return None

    from space.apps.registry.models import Entry

    def _get_agent_config_from_registry(self, agent_id: str) -> dict | None:
        """Load agent configuration from the registry."""
        # Assuming registry.fetch_by_sender can return agent config details
        entry: Entry | None = registry.fetch_by_sender(agent_id)
        if entry:
            return {
                "role": entry.role,
                "model": entry.model,
                "provider": entry.provider,
                "constitution_hash": entry.constitution_hash,
            }
        return None

    def _get_agent_config_from_defaults(self, role: str) -> dict:
        """Load default agent configuration from config.yaml."""
        config_data = config.read()
        return config_data.get("agents", {}).get(role, {})

    def get_agent_config(self, agent_id: str, role: str) -> dict:
        """Get agent configuration from file, then registry, then defaults."""
        config = self._get_agent_config_from_file(agent_id)
        if config:
            return config

        config = self._get_agent_config_from_registry(agent_id)
        if config:
            return config

        return self._get_agent_config_from_defaults(role)

    def spawn(self, role: str, sender_id: str, topic: str) -> dict:
        """Register an agent with the system."""
        agent_config = self.get_agent_config(sender_id, role)

        constitution_path = self.get_constitution_path(role)
        constitution_content = constitution_path.read_text()
        constitution_hash = sha256.sha256(constitution_content)

        # Track constitution in registry_db
        registry.track_constitution(constitution_hash, constitution_content)

        # Link agent in registry
        registry.link(
            agent_id=sender_id,
            role=role,
            channels=[topic],
            constitution_hash=constitution_hash,
            constitution_content=constitution_content,
            provider=agent_config.get("provider"),
            model=agent_config.get("model"),
        )

        return {
            "agent_id": sender_id,
            "role": role,
            "topic": topic,
            "constitution_hash": constitution_hash,
        }

    def launch_agent(
        self,
        role: str,
        agent: str | None,
        extra_args: list[str],
        model: str | None,
        provider: str | None,
        self_description: str | None,
    ):
        """Launches an agent process."""
        agent_id = agent if agent else role  # Use agent if provided, else role
        topic = f"{role}-{agent_id}"  # Derive topic from role and agent_id

        # Register the agent first
        self.spawn(role, agent_id, topic)

        # Construct the command to launch the agent
        command_parts = [
            "poetry",
            "run",
            "python",
            "-m",
            "space.agent",  # Assuming space.agent is the entry point for agents
            role,  # Positional argument for role
            agent_id,  # Positional argument for agent_id
            f"--topic={topic}",
        ]

        if model:
            command_parts.append(f"--model={model}")
        if provider:
            command_parts.append(f"--provider={provider}")
        if self_description:
            command_parts.append(f"--self-description={self_description}")

        command_parts.extend(extra_args)

        full_command = shlex.join(command_parts)
        print(f"Launching agent with command: {full_command}")

        # Execute the command in a new process
        subprocess.Popen(full_command, shell=True)


spawner = Spawner()


def spawn(role: str, sender_id: str, topic: str) -> dict:
    return spawner.spawn(role, sender_id, topic)
