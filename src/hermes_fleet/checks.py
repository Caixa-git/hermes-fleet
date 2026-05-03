"""
Reusable check functions (v0.2+).

Pure validation functions that inspect structured data and return
check results. No file I/O — callers are responsible for loading data.

Each function accepts a dict and returns a single result dict:
    {"check": str, "status": "passed"|"failed"|"skipped", "message": str}

See `safe_defaults.py` for the file-I/O layer that loads data
and calls these functions.
"""

from typing import Dict, List


def _ok(check: str, message: str = "") -> dict:
    return {"check": check, "status": "passed", "message": message}


def _fail(check: str, message: str) -> dict:
    return {"check": check, "status": "failed", "message": message}


def _skip(check: str, message: str) -> dict:
    return {"check": check, "status": "skipped", "message": message}


def _check_name(fn) -> str:
    """Derive a human-readable check name from a function name."""
    return fn.__name__.replace("_", " ").title()


# ──────────────────────────────────────────────
# Docker Compose Checks
# ──────────────────────────────────────────────


def check_no_privileged_containers(compose: dict) -> dict:
    """No service should run in privileged mode."""
    for svc_name, svc in compose.get("services", {}).items():
        if svc.get("privileged", False):
            return _fail(
                _check_name(check_no_privileged_containers),
                f"Service '{svc_name}' has privileged: true",
            )
    return _ok(_check_name(check_no_privileged_containers))


def check_no_docker_sock_mounts(compose: dict) -> dict:
    """No service should mount the Docker socket."""
    for svc_name, svc in compose.get("services", {}).items():
        for vol in svc.get("volumes", []):
            src = vol.get("source", "") if isinstance(vol, dict) else str(vol).split(":")[0]
            if "docker.sock" in src or "/var/run/docker" in src:
                return _fail(
                    _check_name(check_no_docker_sock_mounts),
                    f"Service '{svc_name}' mounts docker socket: {src}",
                )
    return _ok(_check_name(check_no_docker_sock_mounts))


def check_no_host_network_mode(compose: dict) -> dict:
    """No service should use host network mode."""
    for svc_name, svc in compose.get("services", {}).items():
        if svc.get("network_mode") == "host":
            return _fail(
                _check_name(check_no_host_network_mode),
                f"Service '{svc_name}' uses host network mode",
            )
    return _ok(_check_name(check_no_host_network_mode))


def check_all_services_have_cap_drop_all(compose: dict) -> dict:
    """Every service must drop all capabilities."""
    for svc_name, svc in compose.get("services", {}).items():
        if "ALL" not in svc.get("cap_drop", []):
            return _fail(
                _check_name(check_all_services_have_cap_drop_all),
                f"Service '{svc_name}' missing cap_drop: [ALL]",
            )
    return _ok(_check_name(check_all_services_have_cap_drop_all))


def check_all_services_have_no_new_privileges(compose: dict) -> dict:
    """Every service must have no-new-privileges security opt."""
    for svc_name, svc in compose.get("services", {}).items():
        sec_opt = svc.get("security_opt", [])
        if not any("no-new-privileges" in opt for opt in sec_opt):
            return _fail(
                _check_name(check_all_services_have_no_new_privileges),
                f"Service '{svc_name}' missing no-new-privileges",
            )
    return _ok(_check_name(check_all_services_have_no_new_privileges))


def check_all_services_have_pids_limit(compose: dict) -> dict:
    """Every service must have a PID limit set."""
    for svc_name, svc in compose.get("services", {}).items():
        if svc.get("pids_limit") is None:
            return _fail(
                _check_name(check_all_services_have_pids_limit),
                f"Service '{svc_name}' missing pids_limit",
            )
    return _ok(_check_name(check_all_services_have_pids_limit))


def check_all_services_have_read_only_root(compose: dict) -> dict:
    """Every service must have read_only: true."""
    for svc_name, svc in compose.get("services", {}).items():
        if svc.get("read_only") is not True:
            return _fail(
                _check_name(check_all_services_have_read_only_root),
                f"Service '{svc_name}' missing read_only: true",
            )
    return _ok(_check_name(check_all_services_have_read_only_root))


# ──────────────────────────────────────────────
# All Docker Compose Checks
# ──────────────────────────────────────────────


DOCKER_COMPOSE_CHECKS = [
    check_no_privileged_containers,
    check_no_docker_sock_mounts,
    check_no_host_network_mode,
    check_all_services_have_cap_drop_all,
    check_all_services_have_no_new_privileges,
    check_all_services_have_pids_limit,
    check_all_services_have_read_only_root,
]


def run_docker_compose_checks(compose: dict) -> List[dict]:
    """Run all Docker compose checks against a compose dict."""
    return [fn(compose) for fn in DOCKER_COMPOSE_CHECKS]
