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
            yaml.dump({"fleet_version": "0.1.0", "name": "test-fleet", "team": team_id}, f)

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


class TestValidateCommand:
    """Tests for the validate command."""

    runner = CliRunner()

    def test_validate_passes_with_real_presets(self, monkeypatch: pytest.MonkeyPatch):
        """Validate command must pass against the real presets directory."""
        real_presets = Path(__file__).resolve().parent.parent / "presets"

        def mock_get_presets_dir():
            return real_presets

        monkeypatch.setattr("hermes_fleet.teams._get_presets_dir", mock_get_presets_dir)

        result = self.runner.invoke(app, ["validate"], catch_exceptions=False)

        assert result.exit_code == 0
        assert "all contract checks passed" in result.stdout.lower()

    def test_validate_verbose_shows_passing(self, monkeypatch: pytest.MonkeyPatch):
        """Verbose mode must show individual passing checks."""
        real_presets = Path(__file__).resolve().parent.parent / "presets"

        def mock_get_presets_dir():
            return real_presets

        monkeypatch.setattr("hermes_fleet.teams._get_presets_dir", mock_get_presets_dir)

        result = self.runner.invoke(app, ["validate", "-v"], catch_exceptions=False)

        assert result.exit_code == 0
        # Verbose shows ✓ prefix for individual checks
        assert "team:general-dev.agent:orchestrator" in result.stdout
        assert "role:orchestrator.preset:orchestrator_safe" in result.stdout
        assert "handoff:orchestrator-developer.from_role:orchestrator" in result.stdout

    def test_validate_reports_loaded_counts(self, monkeypatch: pytest.MonkeyPatch):
        """Validate must show how many teams and roles were loaded."""
        real_presets = Path(__file__).resolve().parent.parent / "presets"

        def mock_get_presets_dir():
            return real_presets

        monkeypatch.setattr("hermes_fleet.teams._get_presets_dir", mock_get_presets_dir)

        result = self.runner.invoke(app, ["validate"], catch_exceptions=False)

        assert result.exit_code == 0
        assert "8 teams" in result.stdout
        assert "14 roles" in result.stdout
        assert "4 handoffs" in result.stdout

    def test_validate_fails_on_bad_preset_ref(self, monkeypatch: pytest.MonkeyPatch):
        """Validate must detect a role with an unknown permission_preset."""
        import tempfile

        # Create a temp presets dir with a broken role
        tmp_presets = Path(tempfile.mkdtemp())
        teams_dir = tmp_presets / "teams"
        roles_dir = tmp_presets / "roles"
        perms_dir = tmp_presets / "permissions"
        teams_dir.mkdir(parents=True)
        roles_dir.mkdir(parents=True)
        perms_dir.mkdir(parents=True)

        # One valid preset
        with open(perms_dir / "valid_preset.yaml", "w") as f:
            f.write("id: valid_preset\n")

        # One team with one agent
        with open(teams_dir / "test-team.yaml", "w") as f:
            f.write("id: test-team\nname: Test\n")
            f.write("description: A team\nagents:\n  - test-role\n")

        # One role with a bad permission_preset
        with open(roles_dir / "test-role.yaml", "w") as f:
            f.write("id: test-role\nname: Test Role\n")
            f.write("description: A role\nmission: Test\nnon_goals: None\n")
            f.write("permission_preset: nonexistent_preset\n")
            f.write("allowed_tasks:\n  - test\n")
            f.write("handoff:\n  required_outputs:\n    - report\n")
            f.write("completion_gates:\n  required:\n    - done\n")

        def mock_get_presets_dir():
            return tmp_presets

        monkeypatch.setattr("hermes_fleet.teams._get_presets_dir", mock_get_presets_dir)

        result = self.runner.invoke(app, ["validate"], catch_exceptions=False)

        assert result.exit_code != 0
        assert "failed" in result.stdout.lower()
        assert "test-role" in result.stdout
        assert "nonexistent_preset" in result.stdout
