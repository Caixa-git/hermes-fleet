"""Tests: CLI generate command with cross-reference validation."""

from pathlib import Path

import pytest
import yaml
from typer.testing import CliRunner

from hermes_fleet.cli import app


class TestGenerateCrossReference:
    """Cross-reference validation in the generate command."""

    runner = CliRunner()

    def test_generate_rejects_unknown_role(self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch):
        """A team referencing a nonexistent role must fail with clear error."""
        monkeypatch.chdir(tmp_path)

        # Create .fleet/fleet.yaml
        fleet_dir = tmp_path / ".fleet"
        fleet_dir.mkdir(parents=True)
        with open(fleet_dir / "fleet.yaml", "w") as f:
            yaml.dump({"team": "test-team"}, f)

        # Monkeypatch load_team to return a team with a nonexistent agent
        team_def = {
            "id": "test-team",
            "name": "Test Team",
            "description": "A team with a broken reference",
            "agents": ["existing-role", "nonexistent-role"],
        }

        def mock_load_team(team_id: str):
            return team_def if team_id == "test-team" else None

        monkeypatch.setattr("hermes_fleet.teams.load_team", mock_load_team)

        # Run generate
        result = self.runner.invoke(
            app, ["generate"],
            catch_exceptions=False,
        )

        assert result.exit_code != 0
        assert "unknown roles" in result.stdout.lower()
        assert "nonexistent-role" in result.stdout

    def test_generate_passes_with_valid_team(self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch):
        """A team with all valid roles must not trigger cross-reference errors."""
        monkeypatch.chdir(tmp_path)

        # Create .fleet/fleet.yaml
        fleet_dir = tmp_path / ".fleet"
        fleet_dir.mkdir(parents=True)
        with open(fleet_dir / "fleet.yaml", "w") as f:
            yaml.dump({"team": "general-dev"}, f)

        # Override presets dir to point to real presets
        real_presets = Path(__file__).resolve().parent.parent / "presets"

        def mock_get_presets_dir():
            return real_presets

        monkeypatch.setattr("hermes_fleet.teams._get_presets_dir", mock_get_presets_dir)

        # Run generate — it should pass cross-ref check and proceed to generation
        result = self.runner.invoke(
            app, ["generate"],
            catch_exceptions=False,
        )

        # Key assertion: must NOT fail with "unknown roles"
        assert "unknown roles" not in result.stdout.lower()
