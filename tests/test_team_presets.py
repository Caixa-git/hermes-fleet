"""
Tests: Team presets can be loaded correctly.
"""

from pathlib import Path

import pytest
import yaml

from hermes_fleet.teams import load_team, list_available_teams


PRESETS_DIR = Path(__file__).resolve().parent.parent / "presets" / "teams"


class TestTeamPresets:
    """Tests for team preset loading."""

    def test_presets_dir_exists(self):
        assert PRESETS_DIR.exists(), "presets/teams/ directory must exist"
        assert PRESETS_DIR.is_dir()

    def test_general_dev_team_can_be_loaded(self):
        team = load_team("general-dev")
        assert team is not None, "general-dev team preset must be loadable"
        assert "agents" in team, "Team definition must have 'agents' list"
        assert len(team["agents"]) >= 3, "general-dev must have at least 3 agents"

    def test_saas_medium_team_can_be_loaded(self):
        team = load_team("saas-medium")
        assert team is not None, "saas-medium team preset must be loadable"
        assert "agents" in team, "Team definition must have 'agents' list"
        assert len(team["agents"]) >= 5, "saas-medium must have at least 5 agents"

    def test_team_has_required_fields(self):
        for team_file in PRESETS_DIR.glob("*.yaml"):
            with open(team_file) as f:
                team = yaml.safe_load(f)
            assert "id" in team, f"Team {team_file.name} must have 'id'"
            assert "name" in team, f"Team {team_file.name} must have 'name'"
            assert "agents" in team, f"Team {team_file.name} must have 'agents' list"
            assert isinstance(team["agents"], list), f"Team {team_file.name} agents must be a list"

    def test_all_agents_have_corresponding_role_files(self):
        roles_dir = Path(__file__).resolve().parent.parent / "presets" / "roles"
        assert roles_dir.exists(), "presets/roles/ directory must exist"

        for team_file in PRESETS_DIR.glob("*.yaml"):
            with open(team_file) as f:
                team = yaml.safe_load(f)
            for agent_id in team.get("agents", []):
                role_file = roles_dir / f"{agent_id}.yaml"
                assert role_file.exists(), (
                    f"Agent '{agent_id}' in team '{team['id']}' has no role file: {role_file}"
                )

    def test_team_list_available(self):
        teams = list_available_teams()
        assert "general-dev" in teams
        assert "saas-medium" in teams
        assert len(teams) >= 2

    def test_team_validation_rejects_bad_yaml(self):
        """A team YAML without required fields must raise ContractValidationError."""
        from hermes_fleet.contracts import ContractValidationError, team_from_dict

        with pytest.raises(ContractValidationError):
            team_from_dict({"id": "bad-team", "agents": []})

    def test_role_validation_rejects_bad_yaml(self):
        """A role YAML without required fields must raise ContractValidationError."""
        from hermes_fleet.contracts import ContractValidationError, role_from_dict

        with pytest.raises(ContractValidationError):
            role_from_dict({"id": "bad-role", "allowed_tasks": []})
