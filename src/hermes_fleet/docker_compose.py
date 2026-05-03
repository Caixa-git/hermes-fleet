"""
Docker Compose service configuration generation.
"""

from hermes_fleet.network import (
    resolve_network_mode,
    select_networks,
    should_publish_ports,
    get_token_budget,
)
from hermes_fleet.policy import compose_policy


def _sanitize_name(name: str) -> str:
    """Sanitize an agent ID for use in Docker names."""
    return name.replace("_", "-").replace(".", "-").lower()


def _get_agent_state(
    agent_id: str,
    agent_states: dict[str, dict[str, str]] | None = None,
) -> str:
    """Resolve the agent's lifecycle state. Defaults to 'active'."""
    if agent_states and agent_id in agent_states:
        entry = agent_states[agent_id]
        if isinstance(entry, dict):
            return entry.get("state", "active")
    return "active"


def generate_docker_compose(
    team_id: str, agents: list[str],
    resources: dict[str, dict[str, str]] | None = None,
    network_policy: dict | None = None,
    token_budget: dict | None = None,
    agent_states: dict[str, dict[str, str]] | None = None,
) -> dict:
    """
    Generate a complete Docker Compose dict for a team.

    Args:
        team_id: Team preset ID.
        agents: List of agent IDs.
        resources: Optional resource overrides from fleet.yaml.
        network_policy: Optional network policy from fleet.yaml.
            Format: {"default": "isolated", "per_agent": {agent_id: "proxy"}}.
        token_budget: Optional token budget from fleet.yaml.
            Format: {"default": 50, "per_agent": {agent_id: 100}}.
        agent_states: Optional per-agent state from fleet.yaml.
            Format: {"agent_id": {"state": "idle"}}.

    Returns a dict ready for YAML serialization.
    """
    services = {}
    networks = _get_network_definitions()
    volumes = {}
    resources = resources or {}
    default_cpu = resources.get("default_cpu", "0.5")
    default_memory = resources.get("default_memory", "512M")

    for agent_id in agents:
        policy = compose_policy(agent_id)
        sanitized_id = _sanitize_name(agent_id)
        volume_name = f"{sanitized_id}_data"
        worktree_dir = agent_id.replace("-", "_")

        # v0.4: Resolve network mode from fleet.yaml policy or role default
        net_mode = resolve_network_mode(agent_id, network_policy)
        net_list = select_networks(net_mode)
        publish_port = should_publish_ports(net_mode, agent_id)

        # v0.4: Resolve token budget
        budget = get_token_budget(agent_id, token_budget)

        # Determine read_only status
        workspace_access = policy.get("filesystem", {}).get("writable_paths", [])
        is_read_only = len(workspace_access) == 0

        # Per-agent resource limits
        agent_resources = resources.get(agent_id, {}) or {}
        cpu_limit = agent_resources.get("cpus", default_cpu)
        mem_limit = agent_resources.get("memory", default_memory)

        service = {
            "image": "nousresearch/hermes-agent:latest",
            "container_name": f"hermes-fleet-{sanitized_id}-{team_id}",
            "cap_drop": ["ALL"],
            "cap_add": ["DAC_OVERRIDE", "CHOWN", "FOWNER"],
            "security_opt": ["no-new-privileges:true"],
            "pids_limit": 256,
            "read_only": True,
            "tmpfs": [
                "/tmp:rw,noexec,nosuid,size=512m",
                "/run:rw,noexec,nosuid,size=64m",
            ],
            "volumes": [
                f"{volume_name}:/opt/data",
                {
                    "type": "bind",
                    "source": f"./{worktree_dir}",
                    "target": f"/workspace/{worktree_dir}",
                    "read_only": is_read_only,
                },
            ],
            "environment": [
                f"HERMES_PROFILE={agent_id}",
                f"HERMES_MAX_ITERATIONS={budget}",
                f"HERMES_NETWORK_MODE={net_mode}",
                f"HERMES_AGENT_STATE={_get_agent_state(agent_id, agent_states)}",
            ],
            "networks": net_list,
            "deploy": {
                "resources": {
                    "limits": {
                        "cpus": cpu_limit,
                        "memory": mem_limit,
                    }
                }
            },
            "healthcheck": {
                "test": ["CMD-SHELL", "pgrep -f 'hermes' || exit 1"],
                "interval": "30s",
                "timeout": "10s",
                "retries": 3,
                "start_period": "40s",
            },
            "restart": "unless-stopped",
        }

        # v0.4: Only orchestrator and extern-mode agents get published ports
        if publish_port:
            service["ports"] = ["127.0.0.1:8080:8080"]

        services[agent_id] = service
        volumes[volume_name] = {"driver": "local"}

    compose = {
        "services": services,
        "volumes": volumes,
        "networks": networks,
    }

    return compose


def _get_network_definitions() -> dict:
    """Return the network definitions used by all services."""
    return {
        "fleet-no-net": {
            "driver": "bridge",
            "internal": True,
            "name": "hermes-fleet-isolated",
        },
        "fleet-control-plane": {
            "driver": "bridge",
            "internal": True,
            "name": "hermes-fleet-control",
        },
        "fleet-web": {
            "driver": "bridge",
            "name": "hermes-fleet-web",
        },
    }
