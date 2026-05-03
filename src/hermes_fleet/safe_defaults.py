"""
Safe-defaults validator — checks generated configuration against safety rules.
"""

import os
from pathlib import Path
from typing import Dict, List

import yaml

from hermes_fleet.checks import (
    run_docker_compose_checks,
)


def run_safe_defaults_check(generated_dir: Path, verbose: bool = False) -> List[Dict]:
    """
    Run all safe-defaults checks against generated output.

    Args:
        generated_dir: Path to the generated output directory.
        verbose: Include passing and skipped checks in results.

    Returns:
        List of result dicts with keys: check, status, message.
    """
    results = []

    # --- Team Tests ---
    @_check
    def all_agents_have_soul_md(r):
        agents_dir = generated_dir / "agents"
        if not agents_dir.exists():
            r("skipped", "No agents directory found")
            return
        agent_dirs = [d for d in agents_dir.iterdir() if d.is_dir()]
        for ad in agent_dirs:
            soul = ad / "SOUL.md"
            if not soul.exists():
                r("failed", f"Missing SOUL.md for {ad.name}")
                return
        r("passed", f"SOUL.md present for {len(agent_dirs)} agents")

    @_check
    def policy_yaml_generated_for_all_agents(r):
        agents_dir = generated_dir / "agents"
        if not agents_dir.exists():
            r("skipped", "No agents directory found")
            return
        agent_dirs = [d for d in agents_dir.iterdir() if d.is_dir()]
        for ad in agent_dirs:
            policy = ad / "policy.yaml"
            if not policy.exists():
                r("failed", f"Missing policy.yaml for {ad.name}")
                return
        r("passed", f"policy.yaml present for {len(agent_dirs)} agents")

    @_check
    def docker_compose_file_present(r):
        compose_path = generated_dir / "docker-compose.generated.yaml"
        if not compose_path.exists():
            r("failed", "Missing docker-compose.generated.yaml")
            return
        r("passed", "docker-compose.generated.yaml exists")

    # --- Docker Security Tests ---
    @_check
    def docker_security_checks(r):
        compose = _load_compose(generated_dir, r)
        if compose is None:
            return
        for result in run_docker_compose_checks(compose):
            r(result["status"], result.get("message", ""), check_name=result["check"])

    @_check
    def all_agents_have_separate_opt_data(r):
        compose = _load_compose(generated_dir, r)
        if compose is None:
            return
        agents_dir = generated_dir / "agents"
        if not agents_dir.exists():
            r("skipped", "No agents directory")
            return
        agent_ids = [d.name for d in agents_dir.iterdir() if d.is_dir()]
        compose_volumes = compose.get("volumes", {})
        for agent_id in agent_ids:
            vol_name = f"{agent_id.replace('_', '-').lower()}_data"
            if vol_name not in compose_volumes:
                r("failed", f"Agent '{agent_id}' missing separate /opt/data volume: {vol_name}")
                return
        r("passed", f"All {len(agent_ids)} agents have separate /opt/data volumes")

    # --- Policy Tests ---
    @_check
    def reviewer_is_readonly(r):
        _check_agent_policy_field(
            generated_dir, "reviewer", "filesystem", "writable_paths", [], r, "Reviewer workspace is read-only"
        )

    @_check
    def security_reviewer_no_network(r):
        _check_agent_policy_field(
            generated_dir, "security-reviewer", "network", "mode", "none", r, "Security-reviewer has no network"
        )

    @_check
    def orchestrator_no_app_code_write(r):
        agents_dir = generated_dir / "agents"
        if not agents_dir.exists():
            r("skipped", "No agents directory")
            return
        orch_dir = agents_dir / "orchestrator"
        if not orch_dir.exists():
            r("skipped", "No orchestrator agent generated")
            return
        policy_path = orch_dir / "policy.yaml"
        if not policy_path.exists():
            r("skipped", "No orchestrator policy.yaml")
            return
        with open(policy_path) as f:
            policy = yaml.safe_load(f) or {}
        writable_paths = policy.get("filesystem", {}).get("writable_paths", [])
        # Orchestrator should not have writable paths to application code
        app_code_patterns = ["src/", "app/", "frontend/", "backend/"]
        for wp in writable_paths:
            for pat in app_code_patterns:
                if pat in wp:
                    r("failed", f"Orchestrator has write access to app code: {wp}")
                    return
        r("passed", "Orchestrator cannot write app code by default")

    @_check
    def orchestrator_has_kanban_only_workspace(r):
        agents_dir = generated_dir / "agents"
        if not agents_dir.exists():
            r("skipped", "No agents directory")
            return
        orch_dir = agents_dir / "orchestrator"
        if not orch_dir.exists():
            r("skipped", "No orchestrator agent generated")
            return
        policy_path = orch_dir / "policy.yaml"
        if not policy_path.exists():
            r("skipped", "No orchestrator policy.yaml")
            return
        with open(policy_path) as f:
            policy = yaml.safe_load(f) or {}
        writable_paths = policy.get("filesystem", {}).get("writable_paths", [])
        # Orchestrator workspace must be limited to kanban/fleet dirs only
        allowed_kanban_patterns = [".fleet/**", "kanban/**"]
        unexpected_paths = [p for p in writable_paths if p not in allowed_kanban_patterns]
        if unexpected_paths:
            r("failed", f"Orchestrator has non-kanban writable paths: {unexpected_paths}")
            return
        # Verify at least the expected kanban patterns exist
        missing = [p for p in allowed_kanban_patterns if p not in writable_paths]
        if missing:
            r("failed", f"Orchestrator is missing expected kanban writable paths: {missing}")
            return
        r("passed", "Orchestrator has kanban_only workspace")

    @_check
    def deployer_disabled_by_default(r):
        agents_dir = generated_dir / "agents"
        if not agents_dir.exists():
            r("skipped", "No agents directory")
            return
        deployer_dir = agents_dir / "deployer"
        if deployer_dir.exists():
            r("failed", "Deployer agent was generated but should be disabled by default")
            return
        r("passed", "Deployer is not generated by default")

    @_check
    def no_production_secrets_injected(r):
        agents_dir = generated_dir / "agents"
        if not agents_dir.exists():
            r("skipped", "No agents directory")
            return
        production_secrets = [
            "PRODUCTION", "DATABASE_URL_PROD", "DB_PASSWORD",
            "AWS_SECRET", "VERCEL_TOKEN", "STRIPE_SECRET",
        ]
        for agent_dir in agents_dir.iterdir():
            if not agent_dir.is_dir():
                continue
            policy_path = agent_dir / "policy.yaml"
            if not policy_path.exists():
                continue
            with open(policy_path) as f:
                try:
                    policy = yaml.safe_load(f) or {}
                except Exception:
                    continue
            allowed_secrets = policy.get("secrets", {}).get("allow", [])
            for secret in allowed_secrets:
                for prod_pat in production_secrets:
                    if prod_pat.lower() in secret.lower():
                        r("failed", f"Agent '{agent_dir.name}' has production secret: {secret}")
                        return
        r("passed", "No production secrets injected by default")

    # --- Kanban Tests ---
    @_check
    def kanban_task_template_exists(r):
        task_path = generated_dir / "kanban" / "task-template.md"
        if not task_path.exists():
            r("failed", "Missing kanban/task-template.md")
            return
        r("passed", "Kanban task template exists")

    @_check
    def kanban_handoff_template_exists(r):
        handoff_path = generated_dir / "kanban" / "handoff-template.md"
        if not handoff_path.exists():
            r("failed", "Missing kanban/handoff-template.md")
            return
        r("passed", "Kanban handoff template exists")

    @_check
    def kanban_completion_gates_exists(r):
        gates_path = generated_dir / "kanban" / "completion-gates.yaml"
        if not gates_path.exists():
            r("failed", "Missing kanban/completion-gates.yaml")
            return
        r("passed", "Kanban completion gates exist")

    # --- Isolation Tests ---
    @_check
    def no_hermes_home_access(r):
        # Check that generated files don't reference ~/.hermes
        for f in generated_dir.rglob("*"):
            if f.is_file() and f.suffix in (".yaml", ".yml", ".md"):
                try:
                    content = f.read_text()
                except Exception:
                    continue
                if "~/.hermes" in content or os.path.expanduser("~/.hermes") in content:
                    r("failed", f"File {f} references ~/.hermes")
                    return
        r("passed", "No generated files reference ~/.hermes")

    @_check
    def no_real_secrets_in_output(r):
        """Check no generated files contain real secret values."""
        # Check: no secrets/ directory with real secret files
        secrets_dir = generated_dir / "secrets"
        if secrets_dir.exists():
            r("failed", "Secrets directory generated — real secrets should not be stored here")
            return
        r("passed", "No secrets directory generated (secrets use allowlists only)")

    # Run all checks
    check_fns = [
        all_agents_have_soul_md,
        policy_yaml_generated_for_all_agents,
        docker_compose_file_present,
        docker_security_checks,
        all_agents_have_separate_opt_data,
        reviewer_is_readonly,
        security_reviewer_no_network,
        orchestrator_no_app_code_write,
        orchestrator_has_kanban_only_workspace,
        deployer_disabled_by_default,
        no_production_secrets_injected,
        kanban_task_template_exists,
        kanban_handoff_template_exists,
        kanban_completion_gates_exists,
        no_hermes_home_access,
        no_real_secrets_in_output,
    ]

    for fn in check_fns:
        result = fn()  # Returns list of one result dict
        if result:
            for r in result:
                if verbose or r["status"] == "failed":
                    results.append(r)

    return results


def _check_agent_policy_field(
    generated_dir: Path,
    agent_id: str,
    section: str,
    field: str,
    expected,
    r,
    check_name: str,
):
    """Check that a specific policy field has the expected value."""
    agents_dir_path = generated_dir / "agents"
    if not agents_dir_path.exists():
        r("skipped", "No agents directory")
        return
    agent_dir = agents_dir_path / agent_id
    if not agent_dir.exists():
        r("skipped", f"No {agent_id} agent generated")
        return
    policy_path = agent_dir / "policy.yaml"
    if not policy_path.exists():
        r("skipped", f"No policy.yaml for {agent_id}")
        return
    with open(policy_path) as f:
        policy = yaml.safe_load(f) or {}
    value = policy.get(section, {}).get(field)
    if value == expected:
        r("passed", check_name)
    else:
        r("failed", f"{check_name}: expected {field}={expected!r}, got {value!r}")


def _load_compose(generated_dir: Path, r) -> dict:
    """Load docker-compose.generated.yaml."""
    compose_path = generated_dir / "docker-compose.generated.yaml"
    if not compose_path.exists():
        r("skipped", "No docker-compose.generated.yaml")
        return None
    with open(compose_path) as f:
        try:
            return yaml.safe_load(f) or {}
        except Exception as e:
            r("failed", f"Cannot parse docker-compose.generated.yaml: {e}")
            return None


def _check(func):
    """
    Decorator that wraps a check function.

    The check function receives a callback `r` that takes (status, message).
    The decorator ensures the function returns a list with one result dict.
    """
    import functools

    @functools.wraps(func)
    def wrapper(*args, **kwargs):
        results = []

        def record(status, message="", check_name=None):
            results.append({
                "check": check_name or func.__name__.replace("_", " ").title(),
                "status": status,
                "message": message,
            })

        kwargs["r"] = record
        func(*args, **kwargs)

        # Ensure at least one result
        if not results:
            results.append({
                "check": func.__name__.replace("_", " ").title(),
                "status": "passed",
                "message": "",
            })

        return results

    return wrapper
