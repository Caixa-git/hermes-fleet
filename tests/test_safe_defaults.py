"""
Tests: Safe-defaults validator checks.
"""

import os
import tempfile
from pathlib import Path

import pytest
import yaml

from hermes_fleet.safe_defaults import run_safe_defaults_check


class TestSafeDefaultsValidator:
    """Tests for the safe-defaults validator."""

    @pytest.fixture
    def generated_dir(self, tmp_path):
        """Create a minimal generated directory structure for testing."""
        gen_dir = tmp_path / ".fleet" / "generated"
        agents_dir = gen_dir / "agents"
        kanban_dir = gen_dir / "kanban"
        agents_dir.mkdir(parents=True)
        kanban_dir.mkdir(parents=True)

        # Create minimal policy.yaml for each agent
        agents = [
            "orchestrator", "fullstack-developer", "reviewer",
            "qa-tester", "technical-writer",
        ]
        for agent_id in agents:
            agent_dir = agents_dir / agent_id
            agent_dir.mkdir()
            policy = _make_minimal_policy(agent_id)
            with open(agent_dir / "policy.yaml", "w") as f:
                yaml.dump(policy, f, default_flow_style=False)
            # Create SOUL.md placeholder
            (agent_dir / "SOUL.md").write_text(f"# {agent_id}\n\nIdentity placeholder.")

        # Create Docker Compose
        compose = _make_minimal_compose(agents)
        with open(gen_dir / "docker-compose.generated.yaml", "w") as f:
            yaml.dump(compose, f, default_flow_style=False)

        # Create Kanban templates
        (kanban_dir / "task-template.md").write_text("# Task Contract\n\n...")
        (kanban_dir / "handoff-template.md").write_text("# Handoff Note\n\n...")
        (kanban_dir / "completion-gates.yaml").write_text("gates:\n  test: []\n")

        return gen_dir

    def test_team_checks_pass(self, generated_dir):
        """Safe-defaults validator runs without errors."""
        results = run_safe_defaults_check(generated_dir, verbose=True)
        assert len(results) > 0

    def test_no_privileged_containers_check(self, generated_dir):
        """Check that privileged container detection works."""
        results = run_safe_defaults_check(generated_dir, verbose=True)
        privileged_failures = [
            r for r in results
            if "privileged" in r["check"].lower() and r["status"] == "failed"
        ]
        assert len(privileged_failures) == 0

    def test_no_docker_sock_check(self, generated_dir):
        results = run_safe_defaults_check(generated_dir, verbose=True)
        sock_failures = [
            r for r in results
            if "docker.sock" in r["check"].lower() and r["status"] == "failed"
        ]
        assert len(sock_failures) == 0

    def test_cap_drop_all_check(self, generated_dir):
        results = run_safe_defaults_check(generated_dir, verbose=True)
        cap_failures = [
            r for r in results
            if "cap_drop" in r["check"].lower() and r["status"] == "failed"
        ]
        assert len(cap_failures) == 0

    def test_no_new_privileges_check(self, generated_dir):
        results = run_safe_defaults_check(generated_dir, verbose=True)
        priv_failures = [
            r for r in results
            if "no-new-privileges" in r["check"].lower() or (
                "privileges" in r["check"].lower() and r["status"] == "failed"
            )
        ]
        assert len(priv_failures) == 0

    def test_read_only_root_check(self, generated_dir):
        results = run_safe_defaults_check(generated_dir, verbose=True)
        ro_failures = [
            r for r in results
            if "read_only" in r["check"].lower() and r["status"] == "failed"
        ]
        assert len(ro_failures) == 0

    def test_no_hermes_home_reference(self, generated_dir):
        """Generated files must not reference ~/.hermes."""
        # Write a file that references ~/.hermes, confirm it fails
        bad_dir = generated_dir / "agents" / "bad-agent"
        bad_dir.mkdir(exist_ok=True)
        (bad_dir / "policy.yaml").write_text("path: ~/.hermes/config.yaml\n")

        results = run_safe_defaults_check(generated_dir, verbose=True)
        hermes_failures = [
            r for r in results
            if "hermes" in r["check"].lower() and ".hermes" in r.get("message", "").lower()
               and r["status"] == "failed"
        ]
        assert len(hermes_failures) >= 1

    def test_verbose_shows_passing(self, generated_dir):
        """Verbose mode shows passing checks."""
        results = run_safe_defaults_check(generated_dir, verbose=True)
        passed = [r for r in results if r["status"] == "passed"]
        assert len(passed) > 0

    def test_default_output_is_not_verbose(self, generated_dir):
        """Default mode (not verbose) only shows failures."""
        # First check what passes in verbose mode
        verbose_results = run_safe_defaults_check(generated_dir, verbose=True)
        passing = [r for r in verbose_results if r["status"] == "passed"]

        # Now check non-verbose mode
        results = run_safe_defaults_check(generated_dir, verbose=False)
        # In non-verbose mode, no passing results should leak into returned list
        for r in results:
            assert r["status"] != "passed", (
                f"Passing check leaked into non-verbose results: {r['check']}"
            )
        # Verify at least some passing results exist (but are filtered out)
        assert len(passing) > 0, "There should be passing checks to filter"


def _make_minimal_policy(agent_id: str) -> dict:
    """Create a minimal valid policy dict."""
    ro_agents = ["reviewer", "qa-tester", "technical-writer"]
    is_ro = agent_id in ro_agents
    return {
        "agent_id": agent_id,
        "role": agent_id.replace("-", " ").title(),
        "task_policy": {
            "allowed_task_types": ["documentation"],
            "forbidden_task_types": ["deployment"],
        },
        "filesystem": {
            "writable_paths": [] if is_ro else ["docs/**"],
            "readonly_paths": ["**"],
            "forbidden_paths": [".env", "secrets/**"],
        },
        "network": {"mode": "none"},
        "secrets": {"allow": []},
        "commands": {"allow": ["cat"], "deny": ["docker"]},
        "handoff": {"required_outputs": ["summary", "files_changed"]},
        "completion_gate": {"required": ["task_complete"]},
    }


def _make_minimal_compose(agents: list) -> dict:
    """Create a minimal valid Docker Compose dict."""
    services = {}
    volumes = {}
    for agent_id in agents:
        vol_name = f"{agent_id.replace('_', '-').lower()}_data"
        services[agent_id] = {
            "image": "test:latest",
            "container_name": f"test-{agent_id}",
            "cap_drop": ["ALL"],
            "cap_add": ["DAC_OVERRIDE"],
            "security_opt": ["no-new-privileges:true"],
            "pids_limit": 256,
            "read_only": True,
            "tmpfs": ["/tmp:rw,noexec,nosuid,size=512m", "/run:rw,noexec,nosuid,size=64m"],
            "volumes": [
                f"{vol_name}:/opt/data",
                {"type": "bind", "source": f"./{agent_id}", "target": f"/workspace/{agent_id}", "read_only": True},
            ],
            "environment": [],
            "networks": ["fleet-no-net"],
            "deploy": {"resources": {"limits": {"cpus": "0.5", "memory": "512M"}}},
        }
        volumes[vol_name] = {"driver": "local"}

    return {
        "version": "3.8",
        "services": services,
        "volumes": volumes,
        "networks": {
            "fleet-no-net": {"driver": "bridge", "internal": True},
        },
    }
