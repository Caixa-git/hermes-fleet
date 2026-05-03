"""Tests: CLI generate command with cross-reference validation."""

from pathlib import Path

import pytest
import yaml
from typer.testing import CliRunner

from hermes_fleet.cli import app


class TestGenerateCrossReference:
    """Cross-reference validation in the generate command."""

    runner = CliRunner()

    def _create_fleet_yaml(self, tmp_path: Path, team_id: str = "test-team"):
        """Helper: create .fleet/fleet.yaml in tmp_path."""
        fleet_dir = tmp_path / ".fleet"
        fleet_dir.mkdir(parents=True)
        with open(fleet_dir / "fleet.yaml", "w") as f:
            yaml.dump({"team": team_id}, f)

    def test_generate_rejects_unknown_role(self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch):
        """A team referencing a nonexistent role must fail with clear error."""
        monkeypatch.chdir(tmp_path)
        self._create_fleet_yaml(tmp_path)

        team_def = {
            "id": "test-team",
            "name": "Test Team",
            "description": "A team with a broken reference",
            "agents": ["existing-role", "nonexistent-role"],
        }

        def mock_load_team(team_id: str):
            return team_def if team_id == "test-team" else None

        monkeypatch.setattr("hermes_fleet.teams.load_team", mock_load_team)

        result = self.runner.invoke(app, ["generate"], catch_exceptions=False)

        assert result.exit_code != 0
        assert "unknown roles" in result.stdout.lower()
        assert "nonexistent-role" in result.stdout

    def test_generate_passes_with_valid_team(self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch):
        """A team with all valid roles must not trigger cross-reference errors."""
        monkeypatch.chdir(tmp_path)
        self._create_fleet_yaml(tmp_path, "general-dev")

        real_presets = Path(__file__).resolve().parent.parent / "presets"

        def mock_get_presets_dir():
            return real_presets

        monkeypatch.setattr("hermes_fleet.teams._get_presets_dir", mock_get_presets_dir)

        result = self.runner.invoke(app, ["generate"], catch_exceptions=False)

        # Must NOT fail with cross-ref errors
        assert "unknown roles" not in result.stdout.lower()
        assert "unknown permission preset" not in result.stdout.lower()

    def test_generate_rejects_unknown_permission_preset(self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch):
        """A role referencing a nonexistent permission preset must fail."""
        monkeypatch.chdir(tmp_path)
        self._create_fleet_yaml(tmp_path)

        team_def = {
            "id": "test-team",
            "name": "Test Team",
            "description": "A team with a bad preset ref",
            "agents": ["orchestrator"],
        }

        def mock_load_team(team_id: str):
            return team_def if team_id == "test-team" else None

        monkeypatch.setattr("hermes_fleet.teams.load_team", mock_load_team)

        # Temp presets dir with only one preset
        tmp_presets = tmp_path / "presets"
        perms_dir = tmp_presets / "permissions"
        perms_dir.mkdir(parents=True)
        with open(perms_dir / "orchestrator_safe.yaml", "w") as f:
            f.write("id: orchestrator_safe\n")

        # Role data with an unknown permission_preset
        role_data = {
            "id": "orchestrator",
            "name": "Orchestrator",
            "description": "Team coordinator",
            "mission": "Coordinate work",
            "non_goals": "Writing application code",
            "permission_preset": "nonexistent_preset",
            "allowed_tasks": ["orchestration"],
            "handoff": {"required_outputs": ["summary"]},
            "completion_gates": {"required": ["handoff_done"]},
        }

        def mock_load_role(role_id: str):
            return role_data if role_id == "orchestrator" else None

        monkeypatch.setattr("hermes_fleet.teams.load_role", mock_load_role)

        def mock_get_presets_dir():
            return tmp_presets

        monkeypatch.setattr("hermes_fleet.teams._get_presets_dir", mock_get_presets_dir)

        result = self.runner.invoke(app, ["generate"], catch_exceptions=False)

        assert result.exit_code != 0
        assert "unknown permission preset" in result.stdout.lower()
        assert "nonexistent_preset" in result.stdout

    def test_all_valid_presets_known(self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch):
        """Every role in presets/roles/ references a real preset in presets/permissions/."""
        from hermes_fleet.teams import _get_presets_dir, list_available_roles, load_role

        # Use real presets
        real_presets = Path(__file__).resolve().parent.parent / "presets"

        def mock_get_presets_dir():
            return real_presets

        monkeypatch.setattr("hermes_fleet.teams._get_presets_dir", mock_get_presets_dir)

        known_presets = {p.stem for p in (real_presets / "permissions").glob("*.yaml")}
        bad = []
        for role_id in list_available_roles():
            role_data = load_role(role_id)
            preset = role_data.get("permission_preset", "")
            if preset and preset not in known_presets:
                bad.append(f"{role_id} -> {preset}")

        assert not bad, f"Roles with unknown permission_presets: {bad}"
