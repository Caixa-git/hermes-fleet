"""
Tests: policy.yaml generation for each agent role.
"""

from pathlib import Path

import pytest
import yaml

from hermes_fleet.policy import compose_policy, list_presets
from hermes_fleet.teams import load_role, load_team

ROLES_DIR = Path(__file__).resolve().parent.parent / "presets" / "roles"


class TestPolicyGeneration:
    """Tests for policy.yaml generation."""

    def test_policy_is_generated_for_every_role(self):
        """Verify policy.yaml is generated for every agent role."""
        for role_file in ROLES_DIR.glob("*.yaml"):
            role_id = role_file.stem
            policy = compose_policy(role_id)
            assert policy is not None
            assert "agent_id" in policy
            assert policy["agent_id"] == role_id

    def test_policy_has_required_sections(self):
        """Every policy must have task_policy, filesystem, network, secrets, commands, handoff."""
        for role_file in ROLES_DIR.glob("*.yaml"):
            role_id = role_file.stem
            policy = compose_policy(role_id)
            assert "task_policy" in policy, f"{role_id} missing task_policy"
            assert "filesystem" in policy, f"{role_id} missing filesystem"
            assert "network" in policy, f"{role_id} missing network"
            assert "secrets" in policy, f"{role_id} missing secrets"
            assert "commands" in policy, f"{role_id} missing commands"
            assert "handoff" in policy, f"{role_id} missing handoff"
            assert "completion_gate" in policy, f"{role_id} missing completion_gate"

    def test_policy_is_valid_yaml(self):
        """Generated policy must be valid YAML."""
        for role_file in ROLES_DIR.glob("*.yaml"):
            role_id = role_file.stem
            policy = compose_policy(role_id)
            # Round-trip through YAML
            yaml_str = yaml.dump(policy, default_flow_style=False)
            reloaded = yaml.safe_load(yaml_str)
            assert reloaded is not None
            assert reloaded["agent_id"] == role_id

    def test_permission_presets_exist(self):
        presets = list_presets()
        assert len(presets) > 0
        assert "orchestrator_safe" in presets
        assert "repo_readonly" in presets
        assert "readonly_no_network" in presets

    def test_security_reviewer_has_no_secrets(self):
        policy = compose_policy("security-reviewer")
        assert policy["secrets"]["allow"] == [], (
            "Security reviewer must have empty secret allowlist"
        )

    def test_security_reviewer_no_network(self):
        policy = compose_policy("security-reviewer")
        assert policy["network"]["mode"] == "none", (
            "Security reviewer must have network mode 'none'"
        )

    def test_reviewer_has_no_writable_paths(self):
        policy = compose_policy("reviewer")
        assert len(policy["filesystem"]["writable_paths"]) == 0, (
            "Reviewer must have no writable paths"
        )

    def test_orchestrator_cannot_write_app_code(self):
        policy = compose_policy("orchestrator")
        writable = policy["filesystem"]["writable_paths"]
        app_code_patterns = ["src/", "app/", "frontend/", "backend/"]
        for wp in writable:
            for pat in app_code_patterns:
                assert pat not in wp, (
                    f"Orchestrator has write access to app code: {wp}"
                )

    def test_every_role_has_handoff_outputs(self):
        for role_file in ROLES_DIR.glob("*.yaml"):
            role_id = role_file.stem
            policy = compose_policy(role_id)
            outputs = policy["handoff"]["required_outputs"]
            assert len(outputs) > 0, f"{role_id} has no handoff required outputs"

    def test_every_role_has_completion_gates(self):
        for role_file in ROLES_DIR.glob("*.yaml"):
            role_id = role_file.stem
            policy = compose_policy(role_id)
            gates = policy["completion_gate"]["required"]
            assert len(gates) > 0, f"{role_id} has no completion gates"

    def test_frontend_developer_has_public_secrets_only(self):
        policy = compose_policy("frontend-developer")
        for secret in policy["secrets"]["allow"]:
            assert not secret.upper().startswith("PROD_"), (
                f"Frontend developer has production secret: {secret}"
            )
            assert "SECRET" not in secret.upper() or "PUBLIC" in secret.upper(), (
                f"Frontend developer has non-public secret: {secret}"
            )
