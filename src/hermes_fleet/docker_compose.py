"""
Docker Compose service configuration generation.
"""

from hermes_fleet.policy import compose_policy


def _sanitize_name(name: str) -> str:
    """Sanitize an agent ID for use in Docker names."""
    return name.replace("_", "-").replace(".", "-").lower()


def _select_network(policy: dict) -> list[str]:
    """Select Docker Compose networks based on policy."""
    network_mode = policy.get("network", {}).get("mode", "none")
    if network_mode in ("control_plane_only", "package_registry"):
        return ["fleet-control-plane"]
    elif network_mode == "web_readonly":
        return ["fleet-web"]
    else:
        return ["fleet-no-net"]


def generate_docker_compose(
    team_id: str, agents: list[str],
    resources: dict[str, dict[str, str]] | None = None,
) -> dict:
    """
    Generate a complete Docker Compose dict for a team.

    Args:
        team_id: Team preset ID.
        agents: List of agent IDs.
        resources: Optional resource overrides from fleet.yaml.
            Keys: agent_id or 'default_cpu'/'default_memory'.
            Format: {"orchestrator": {"cpus": "1.0", "memory": "1G"}, "default_cpu": "0.5"}.

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

        # Determine read_only status
        workspace_access = policy.get("filesystem", {}).get("writable_paths", [])
        is_read_only = len(workspace_access) == 0

        # Per-agent resource limits (v0.2+)
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
            ],
            "networks": _select_network(policy),
            "deploy": {
                "resources": {
                    "limits": {
                        "cpus": cpu_limit,
                        "memory": mem_limit,
                    }
                }
            },
        }

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
