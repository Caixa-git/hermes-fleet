"""
Docker Compose service configuration generation.
"""

from typing import List

from hermes_fleet.policy import compose_policy


def _sanitize_name(name: str) -> str:
    """Sanitize an agent ID for use in Docker names."""
    return name.replace("_", "-").replace(".", "-").lower()


def _select_network(agent_id: str, policy: dict) -> List[str]:
    """Select Docker Compose networks based on policy."""
    network_mode = policy.get("network", {}).get("mode", "none")
    if network_mode == "control_plane_only":
        return ["fleet-control-plane"]
    elif network_mode == "package_registry":
        return ["fleet-control-plane"]
    elif network_mode == "web_readonly":
        return ["fleet-web"]
    elif network_mode == "none":
        return ["fleet-no-net"]
    else:
        return ["fleet-no-net"]


def generate_docker_compose(team_id: str, agents: List[str]) -> dict:
    """
    Generate a complete Docker Compose dict for a team.

    Returns a dict ready for YAML serialization.
    """
    services = {}
    networks = _get_network_definitions()
    volumes = {}

    for agent_id in agents:
        policy = compose_policy(agent_id)
        sanitized_id = _sanitize_name(agent_id)
        volume_name = f"{sanitized_id}_data"
        worktree_dir = agent_id.replace("-", "_")

        # Determine read_only status
        workspace_access = policy.get("filesystem", {}).get("writable_paths", [])
        is_read_only = len(workspace_access) == 0

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
            "networks": _select_network(agent_id, policy),
            "deploy": {
                "resources": {
                    "limits": {
                        "cpus": "0.5",
                        "memory": "512M",
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
