"""
Fleet runner — Docker container lifecycle management.

Executes `docker compose` and `docker` CLI commands via subprocess.
All functions return structured dicts for CLI display and testing.
"""

from __future__ import annotations

import json
import subprocess
from pathlib import Path
from typing import Any


class DockerNotAvailableError(RuntimeError):
    """Raised when Docker is not installed or not running."""


def _check_docker() -> str:
    """Verify Docker is available. Returns version string or raises."""
    try:
        result = subprocess.run(
            ["docker", "--version"],
            capture_output=True, text=True, timeout=10,
        )
        if result.returncode != 0:
            raise DockerNotAvailableError(
                "Docker not available. Install Docker Desktop or the Docker CLI."
            )
        return result.stdout.strip()
    except FileNotFoundError:
        raise DockerNotAvailableError(
            "Docker command not found. Install Docker Desktop or the Docker CLI."
        )


def _compose_file_path(project_dir: Path) -> Path:
    """Return the path to the generated Docker Compose file."""
    return project_dir / ".fleet" / "generated" / "docker-compose.generated.yaml"


def _compose_cmd(args: list[str], project_dir: Path) -> subprocess.CompletedProcess:
    """Run a docker compose command and return the CompletedProcess."""
    compose_file = _compose_file_path(project_dir)
    if not compose_file.exists():
        raise FileNotFoundError(
            f"Docker Compose file not found: {compose_file}\n"
            "Run 'hermes-fleet generate' first."
        )
    cmd = ["docker", "compose", "-f", str(compose_file)] + args
    return subprocess.run(cmd, capture_output=True, text=True, timeout=120)


def _read_fleet_config(project_dir: Path) -> dict[str, Any]:
    """Read fleet.yaml and return the config dict."""
    fleet_yaml = project_dir / ".fleet" / "fleet.yaml"
    if not fleet_yaml.exists():
        return {}
    import yaml
    with open(fleet_yaml) as f:
        return yaml.safe_load(f) or {}


def up(project_dir: Path, detach: bool = True) -> dict[str, Any]:
    """
    Start the fleet.

    Args:
        project_dir: Project root directory.
        detach: Run containers in background (default: True).

    Returns:
        Dict with keys: success, message, details.
    """
    try:
        _check_docker()
    except DockerNotAvailableError as e:
        return {"success": False, "message": str(e), "details": ""}

    try:
        args = ["up"]
        if detach:
            args.append("-d")
        result = _compose_cmd(args, project_dir)
        if result.returncode == 0:
            config = _read_fleet_config(project_dir)
            team = config.get("team", "unknown")
            return {
                "success": True,
                "message": f"Fleet started ({team})",
                "details": result.stdout.strip(),
            }
        else:
            return {
                "success": False,
                "message": "Failed to start fleet",
                "details": result.stderr.strip(),
            }
    except FileNotFoundError as e:
        return {"success": False, "message": str(e), "details": ""}
    except subprocess.TimeoutExpired:
        return {"success": False, "message": "Docker compose up timed out", "details": ""}


def down(project_dir: Path, remove_volumes: bool = False) -> dict[str, Any]:
    """
    Stop the fleet.

    Args:
        project_dir: Project root directory.
        remove_volumes: Remove named volumes (default: False).

    Returns:
        Dict with keys: success, message, details.
    """
    try:
        _check_docker()
    except DockerNotAvailableError as e:
        return {"success": False, "message": str(e), "details": ""}

    try:
        args = ["down"]
        if remove_volumes:
            args.append("-v")
        result = _compose_cmd(args, project_dir)
        if result.returncode == 0:
            return {
                "success": True,
                "message": "Fleet stopped",
                "details": result.stdout.strip(),
            }
        else:
            return {
                "success": False,
                "message": "Failed to stop fleet",
                "details": result.stderr.strip(),
            }
    except FileNotFoundError as e:
        return {"success": False, "message": str(e), "details": ""}
    except subprocess.TimeoutExpired:
        return {"success": False, "message": "Docker compose down timed out", "details": ""}


def status(project_dir: Path) -> dict[str, Any]:
    """
    Check fleet container status.

    Returns:
        Dict with keys: success, message, containers (list of dicts).
        Each container dict: name, status, state, health.
    """
    try:
        _check_docker()
    except DockerNotAvailableError as e:
        return {"success": False, "message": str(e), "containers": []}

    try:
        result = _compose_cmd(["ps", "--format", "json"], project_dir)
        if result.returncode != 0:
            return {"success": False, "message": result.stderr.strip(), "containers": []}

        containers = []
        stdout = result.stdout.strip()
        if stdout:
            for line in stdout.splitlines():
                try:
                    entry = json.loads(line)
                    containers.append({
                        "name": entry.get("Name", ""),
                        "state": entry.get("State", "unknown"),
                        "status": entry.get("Status", ""),
                        "health": entry.get("Health", ""),
                    })
                    # Append health to status if available
                    if containers[-1]["health"]:
                        containers[-1]["status"] += f" ({containers[-1]['health']})"
                except json.JSONDecodeError:
                    pass  # skip malformed lines

        running = sum(1 for c in containers if c["state"] == "running")
        return {
            "success": True,
            "message": f"{running}/{len(containers)} containers running",
            "containers": containers,
        }
    except FileNotFoundError as e:
        return {"success": False, "message": str(e), "containers": []}
    except subprocess.TimeoutExpired:
        return {"success": False, "message": "Docker compose ps timed out", "containers": []}


def _get_container_name(project_dir: Path, agent_id: str) -> str | None:
    """Resolve agent_id to a Docker container name using the compose file."""
    import yaml
    compose_file = _compose_file_path(project_dir)
    if not compose_file.exists():
        return None
    with open(compose_file) as f:
        compose = yaml.safe_load(f) or {}
    services = compose.get("services", {})
    svc = services.get(agent_id)
    if not svc:
        return None
    return svc.get("container_name", f"hermes-fleet-{agent_id}")


def logs(project_dir: Path, agent_id: str, tail: int = 100) -> dict[str, Any]:
    """
    Show logs for a specific agent container.

    Args:
        project_dir: Project root directory.
        agent_id: Agent/service ID.
        tail: Number of lines to show from the end (default: 100).

    Returns:
        Dict with keys: success, message, logs (str).
    """
    try:
        _check_docker()
    except DockerNotAvailableError as e:
        return {"success": False, "message": str(e), "logs": ""}

    try:
        container_name = _get_container_name(project_dir, agent_id)
        if not container_name:
            return {
                "success": False,
                "message": f"Unknown agent: {agent_id}. Available agents listed in fleet.yaml.",
                "logs": "",
            }

        result = subprocess.run(
            ["docker", "logs", "--tail", str(tail), container_name],
            capture_output=True, text=True, timeout=30,
        )
        if result.returncode == 0:
            return {
                "success": True,
                "message": f"Logs for {agent_id}",
                "logs": result.stdout.strip() or result.stderr.strip(),
            }
        else:
            # Non-zero exit usually means container not found or not running
            msg = result.stderr.strip() or result.stdout.strip()
            return {
                "success": False,
                "message": msg or f"Container '{container_name}' not found or not running",
                "logs": "",
            }
    except FileNotFoundError:
        return {"success": False, "message": "Docker command not found", "logs": ""}
    except subprocess.TimeoutExpired:
        return {"success": False, "message": "docker logs timed out", "logs": ""}


def restart(project_dir: Path, agent_id: str) -> dict[str, Any]:
    """
    Restart a specific agent container.

    Args:
        project_dir: Project root directory.
        agent_id: Agent/service ID.

    Returns:
        Dict with keys: success, message, details.
    """
    try:
        _check_docker()
    except DockerNotAvailableError as e:
        return {"success": False, "message": str(e), "details": ""}

    try:
        container_name = _get_container_name(project_dir, agent_id)
        if not container_name:
            return {
                "success": False,
                "message": f"Unknown agent: {agent_id}",
                "details": "",
            }

        result = _compose_cmd(["restart", agent_id], project_dir)
        if result.returncode == 0:
            return {
                "success": True,
                "message": f"Agent '{agent_id}' restarted",
                "details": result.stdout.strip(),
            }
        else:
            return {
                "success": False,
                "message": f"Failed to restart '{agent_id}'",
                "details": result.stderr.strip(),
            }
    except FileNotFoundError as e:
        return {"success": False, "message": str(e), "details": ""}
    except subprocess.TimeoutExpired:
        return {"success": False, "message": "docker restart timed out", "details": ""}
