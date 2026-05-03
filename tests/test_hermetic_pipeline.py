"""
Tests: Hermetic pipeline — init → plan → generate → validate.

Runs the full pipeline in a temp directory. No Docker, no external services.
Verifies that generated output structure matches expectations.
All assertions check file existence, YAML validity, and contract validation.
"""

from pathlib import Path

import pytest
import yaml

from hermes_fleet.planner import recommend_team
from hermes_fleet.generator import generate_fleet


class TestHermeticPipeline:
    """Full pipeline test: init → plan → generate → validate."""

    @pytest.fixture
    def fleet_config(self) -> dict:
        return {
            "fleet_version": "0.2.0",
            "name": "test-fleet",
            "team": "general-dev",
            "output_dir": ".fleet/generated",
            "resources": {
                "default_cpu": "0.5",
                "default_memory": "512M",
            },
        }

    @pytest.fixture
    def project_dir(self, tmp_path, fleet_config) -> Path:
        """Create a minimal project directory with fleet.yaml."""
        fleet_dir = tmp_path / ".fleet"
        fleet_dir.mkdir(parents=True, exist_ok=True)
        fleet_yaml = fleet_dir / "fleet.yaml"
        with open(fleet_yaml, "w") as f:
            yaml.dump(fleet_config, f)
        return tmp_path

    def test_plan_recommends_known_team(self):
        """plan recommends a team that exists in presets."""
        team_id, team_def = recommend_team("build a web application")
        assert team_id is not None
        assert isinstance(team_id, str)
        assert len(team_def.get("agents", [])) >= 1

    def test_plan_recommends_known_team_for_different_goals(self):
        """Different goals should produce different team recommendations."""
        web_team_id, _ = recommend_team("build a web application")
        security_team_id, _ = recommend_team("audit code security")
        assert web_team_id != security_team_id

    def test_generate_creates_all_expected_files(self, project_dir):
        """generate produces all expected files and directories."""
        team_id, team_def = recommend_team("build a web application")
        output_dir = generate_fleet(
            project_dir=project_dir,
            team_id=team_id,
            team_def=team_def,
            force=True,
        )

        assert output_dir.exists()
        assert output_dir.name == "generated"

        # Per-agent configs
        agents_dir = output_dir / "agents"
        assert agents_dir.exists()
        for agent_id in team_def["agents"]:
            agent_dir = agents_dir / agent_id
            assert agent_dir.exists(), f"Missing agent dir: {agent_id}"
            assert (agent_dir / "SOUL.md").exists(), f"Missing SOUL.md for {agent_id}"
            assert (agent_dir / "policy.yaml").exists(), f"Missing policy.yaml for {agent_id}"

        # Docker Compose
        compose_path = output_dir / "docker-compose.generated.yaml"
        assert compose_path.exists()

        # Kanban templates
        kanban_dir = output_dir / "kanban"
        assert kanban_dir.exists()
        assert (kanban_dir / "task-template.md").exists()
        assert (kanban_dir / "handoff-template.md").exists()
        assert (kanban_dir / "completion-gates.yaml").exists()

    def test_generated_compose_is_valid_and_complete(self, project_dir):
        """Generated Docker Compose YAML is valid and contains all services."""
        team_id, team_def = recommend_team("build a web application")
        output_dir = generate_fleet(
            project_dir=project_dir,
            team_id=team_id,
            team_def=team_def,
            force=True,
        )

        compose_path = output_dir / "docker-compose.generated.yaml"
        with open(compose_path) as f:
            compose = yaml.safe_load(f)

        assert "services" in compose
        assert "volumes" in compose
        assert "networks" in compose

        for agent_id in team_def["agents"]:
            svc = compose["services"].get(agent_id)
            assert svc is not None, f"Missing service: {agent_id}"
            # Every service must have minimal security defaults
            assert svc.get("read_only") is True, f"{agent_id}: not read_only"
            assert "ALL" in svc.get("cap_drop", []), f"{agent_id}: missing cap_drop ALL"
            assert svc.get("restart") == "unless-stopped", f"{agent_id}: missing restart"
            # v0.3: healthcheck must be present
            assert "healthcheck" in svc, f"{agent_id}: missing healthcheck"

    def test_generated_policy_has_required_fields(self, project_dir):
        """Every agent's policy.yaml has critical fields."""
        team_id, team_def = recommend_team("build a web application")
        output_dir = generate_fleet(
            project_dir=project_dir,
            team_id=team_id,
            team_def=team_def,
            force=True,
        )

        agents_dir = output_dir / "agents"
        for agent_id in team_def["agents"]:
            policy_path = agents_dir / agent_id / "policy.yaml"
            with open(policy_path) as f:
                policy = yaml.safe_load(f)

            assert "filesystem" in policy, f"{agent_id}: missing filesystem"
            assert "network" in policy, f"{agent_id}: missing network"
            assert "task_policy" in policy, f"{agent_id}: missing task_policy"

    def test_validate_all_contracts_pass(self):
        """validate should pass for all built-in presets."""
        from hermes_fleet.contracts import (
            team_from_dict,
            role_from_dict,
            handoff_from_dict,
            validate_contract_cross_references,
        )
        from hermes_fleet.teams import (
            _get_presets_dir,
            list_available_teams,
            list_available_roles,
            list_available_handoffs,
            load_team,
            load_role,
            load_handoff,
        )

        presets_dir = _get_presets_dir()
        known_presets = [p.stem for p in (presets_dir / "permissions").glob("*.yaml")]

        teams = []
        for team_id in list_available_teams():
            data = load_team(team_id)
            if data is not None:
                teams.append(team_from_dict(data))

        roles = []
        for role_id in list_available_roles():
            data = load_role(role_id)
            if data is not None:
                roles.append(role_from_dict(data))

        handoffs = {}
        for hid in list_available_handoffs():
            data = load_handoff(hid)
            if data is not None:
                hc = handoff_from_dict(data)
                handoffs[hc.id] = hc

        results = validate_contract_cross_references(
            teams, roles,
            known_presets=known_presets,
            handoff_contracts=handoffs,
        )

        failures = [r for r in results if r.status == "failed"]
        assert len(failures) == 0, f"Validation failures:\n" + "\n".join(
            f"  {r.check}: {r.message}" for r in failures
        )
