"""
Reusable check functions (v0.2+).

Pure validation functions that inspect structured data and return
check results. No file I/O — callers are responsible for loading data.

Each function accepts a dict and returns a single result dict:
    {"check": str, "status": "passed"|"failed"|"skipped", "message": str}

See `safe_defaults.py` for the file-I/O layer that loads data
and calls these functions.
"""

from typing import List


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
# Three-Pillar Role Adoption Gate (v0.2+)
# ──────────────────────────────────────────────


PILLAR_ROLE = "Role"
PILLAR_BOUNDARY = "Boundary"
PILLAR_COMPLETION = "Completion"


def _check_pillar_role(role_id: str, data: dict) -> list[dict]:
    """Pillar 1 — Role Fidelity: role identity must be complete."""
    results = []
    required = [
        ("id", "Role ID"),
        ("name", "Role name"),
        ("description", "Role description"),
        ("mission", "Role mission"),
    ]
    for field, label in required:
        val = data.get(field, "")
        if not val or (isinstance(val, str) and not val.strip()):
            results.append(_fail(
                f"pillar:role:{role_id}",
                f"{label} is empty or missing for role '{role_id}'",
            ))
    # non_goals is recommended but not required for simpler roles
    if "non_goals" not in data or not isinstance(data.get("non_goals"), str):
        results.append(_skip(
            f"pillar:role:{role_id}",
            f"Non-goals not set for role '{role_id}' — recommended but not required",
        ))
    if not results:
        results.append(_ok(f"pillar:role:{role_id}", f"Role '{role_id}' passes Role pillar"))
    return results


def _check_pillar_boundary(role_id: str, data: dict, known_presets: set[str]) -> list[dict]:
    """Pillar 2 — Boundary/Isolation: permissions and task boundaries."""
    results = []
    preset = data.get("permission_preset", "")
    if not preset:
        results.append(_fail(
            f"pillar:boundary:{role_id}",
            f"No permission_preset for role '{role_id}'",
        ))
    elif preset not in known_presets:
        results.append(_fail(
            f"pillar:boundary:{role_id}",
            f"Permission preset '{preset}' for role '{role_id}' does not exist",
        ))
    tasks = data.get("allowed_tasks", [])
    if not tasks:
        results.append(_fail(
            f"pillar:boundary:{role_id}",
            f"No allowed_tasks defined for role '{role_id}'",
        ))
    forbidden = data.get("forbidden_tasks", [])
    if not forbidden:
        results.append(_skip(
            f"pillar:boundary:{role_id}",
            f"No forbidden_tasks for role '{role_id}' — recommend at least one",
        ))
    if not results:
        results.append(_ok(f"pillar:boundary:{role_id}", f"Role '{role_id}' passes Boundary pillar"))
    return results


def _check_pillar_completion(role_id: str, data: dict) -> list[dict]:
    """Pillar 3 — Completion: handoff readiness and gates."""
    results = []
    handoff_contract = data.get("handoff_contract")
    inline_handoff = data.get("handoff", {}) or {}
    has_handoff = bool(handoff_contract) or bool(inline_handoff.get("required_outputs"))
    if not has_handoff:
        results.append(_fail(
            f"pillar:completion:{role_id}",
            f"No handoff_contract reference or inline handoff outputs for role '{role_id}'",
        ))
    gates = data.get("completion_gates", {}) or {}
    required_gates = gates.get("required", [])
    if not required_gates:
        results.append(_skip(
            f"pillar:completion:{role_id}",
            f"No completion gates for role '{role_id}' — recommend at least one gate",
        ))
    if not results:
        results.append(_ok(f"pillar:completion:{role_id}", f"Role '{role_id}' passes Completion pillar"))
    return results


def run_role_adoption_gate(roles: list[dict], known_presets: set[str]) -> list[dict]:
    """Run all three pillar checks against every role.

    Args:
        roles: List of raw role dicts (from YAML).
        known_presets: Set of valid permission preset IDs.

    Returns:
        List of check result dicts with check/status/message keys.
    """
    results = []
    pillar_counts: dict[str, dict[str, int]] = {}
    for role_data in roles:
        role_id = role_data.get("id", "unknown")
        pillar_counts[role_id] = {"passed": 0, "failed": 0, "skipped": 0}
        for check_fn, pillar_name in [
            (_check_pillar_role, "Role"),
            (_check_pillar_boundary, "Boundary"),
            (_check_pillar_completion, "Completion"),
        ]:
            if pillar_name == "Boundary":
                sub_results = check_fn(role_id, role_data, known_presets)
            else:
                sub_results = check_fn(role_id, role_data)
            for sr in sub_results:
                pillar_counts[role_id][sr["status"]] += 1
                results.append(sr)
    # Summary
    total_passed = sum(c["passed"] for c in pillar_counts.values())
    total_failed = sum(c["failed"] for c in pillar_counts.values())
    total_skipped = sum(c["skipped"] for c in pillar_counts.values())
    results.append(_ok(
        "pillar:summary",
        f"3-pillar gate: {len(roles)} roles, {total_passed} passed, "
        f"{total_failed} failed, {total_skipped} skipped",
    ))
    return results


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
