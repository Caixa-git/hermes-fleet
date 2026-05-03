"""
Tests: End-to-end integration tests for hermes-fleet.
"""

import tempfile
from pathlib import Path

import pytest
import yaml

from hermes_fleet.generator import generate_fleet
from hermes_fleet.teams import load_team


class TestEndToEnd:
    """End-to-end tests for the full generate flow."""

    @pytest.mark.parametrize("team_id", ["general-dev", "saas-medium"])
    def test_generate_fleet_end_to_end(self, team_id, tmp_path):
        """Full generate pipeline produces expected output."""
        team_def = load_team(team_id)
        assert team_def is not None

        output_dir = generate_fleet(
            project_dir=tmp_path,
            team_id=team_id,
            team_def=team_def,
            force=True,
        )

        assert output_dir.exists()
        assert (output_dir / "docker-compose.generated.yaml").exists()
        assert (output_dir / "kanban" / "task-template.md").exists()
        assert (output_dir / "kanban" / "handoff-template.md").exists()
        assert (output_dir / "kanban" / "completion-gates.yaml").exists()

        # Verify each agent has SOUL.md and policy.yaml
        agents_dir = output_dir / "agents"
        for agent_id in team_def["agents"]:
            agent_dir = agents_dir / agent_id
            assert agent_dir.is_dir(), f"Agent directory missing: {agent_id}"
            assert (agent_dir / "SOUL.md").exists(), f"SOUL.md missing for {agent_id}"
            assert (agent_dir / "policy.yaml").exists(), f"policy.yaml missing for {agent_id}"

    def test_docker_compose_is_valid_yaml(self, tmp_path):
        """Generated Docker Compose must be valid YAML."""
        team = load_team("general-dev")
        output = generate_fleet(tmp_path, "general-dev", team, force=True)
        compose_path = output / "docker-compose.generated.yaml"

        with open(compose_path) as f:
            compose = yaml.safe_load(f)

        assert compose is not None
        assert "services" in compose
        assert compose["version"] == "3.8"

    def test_output_is_deterministic(self, tmp_path):
        """Same input produces identical output."""
        team = load_team("general-dev")

        output1 = generate_fleet(tmp_path / "run1", "general-dev", team, force=True)
        output2 = generate_fleet(tmp_path / "run2", "general-dev", team, force=True)

        # Compare file contents
        for fname in ["docker-compose.generated.yaml"]:
            content1 = (output1 / fname).read_text()
            content2 = (output2 / fname).read_text()
            assert content1 == content2, f"{fname} output is not deterministic"

    def test_no_hermes_home_in_output(self, tmp_path):
        """Generated output must not reference ~/.hermes."""
        team = load_team("general-dev")
        output = generate_fleet(tmp_path, "general-dev", team, force=True)

        for f in output.rglob("*"):
            if f.is_file():
                content = f.read_text()
                assert "~/.hermes" not in content, (
                    f"Generated file {f} references ~/.hermes"
                )

    def test_no_real_secrets_in_output(self, tmp_path):
        """Generated output must not contain real secret values."""
        team = load_team("saas-medium")
        output = generate_fleet(tmp_path, "saas-medium", team, force=True)

        secret_patterns = ["password", "secret_key", "api_key_actual", "token_real"]
        for f in output.rglob("*"):
            if f.is_file() and f.suffix in (".yaml", ".yml", ".md"):
                content = f.read_text().lower()
                for pattern in secret_patterns:
                    assert pattern not in content, (
                        f"Generated file {f} may contain real secret: {pattern}"
                    )

    def test_all_agents_have_policy_yaml(self, tmp_path):
        """Every agent in every team must have a policy.yaml."""
        for team_id in ["general-dev", "saas-medium"]:
            team = load_team(team_id)
            output = generate_fleet(tmp_path / team_id, team_id, team, force=True)

            for agent_id in team["agents"]:
                policy_path = output / "agents" / agent_id / "policy.yaml"
                assert policy_path.exists(), f"Missing policy.yaml for {agent_id} in {team_id}"

                with open(policy_path) as f:
                    policy = yaml.safe_load(f)
                assert policy is not None
                assert policy["agent_id"] == agent_id
