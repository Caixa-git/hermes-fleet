"""Tests: CLI plan and init commands."""

from pathlib import Path

import pytest
import yaml
from typer.testing import CliRunner

from hermes_agency.cli import app


class TestInitCommand:
    """Tests for init command."""

    runner = CliRunner()

    def test_init_creates_fleet_yaml(self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch):
        """init must create .fleet/fleet.yaml with defaults."""
        monkeypatch.chdir(tmp_path)
        result = self.runner.invoke(app, ["init"], catch_exceptions=False)
        assert result.exit_code == 0
        fleet_yaml = tmp_path / ".fleet" / "fleet.yaml"
        assert fleet_yaml.exists()
        config = yaml.safe_load(fleet_yaml.read_text())
        assert config["name"] == tmp_path.name
        assert config["team"] == "general-dev"

    def test_init_creates_lock_files(self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch):
        """init must create foundation.lock.yaml and agency.lock.yaml."""
        monkeypatch.chdir(tmp_path)
        result = self.runner.invoke(app, ["init"], catch_exceptions=False)
        assert result.exit_code == 0
        assert (tmp_path / ".fleet" / "foundation.lock.yaml").exists()
        assert (tmp_path / ".fleet" / "agency.lock.yaml").exists()

    def test_init_idempotent(self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch):
        """Running init twice must not fail."""
        monkeypatch.chdir(tmp_path)
        r1 = self.runner.invoke(app, ["init"], catch_exceptions=False)
        r2 = self.runner.invoke(app, ["init"], catch_exceptions=False)
        assert r1.exit_code == 0
        assert r2.exit_code == 0


class TestPlanCommand:
    """Tests for plan command."""

    runner = CliRunner()

    def test_plan_recommends_team(self, monkeypatch: pytest.MonkeyPatch):
        """plan must output a team recommendation."""
        result = self.runner.invoke(app, ["plan", "Build a SaaS platform"], catch_exceptions=False)
        assert result.exit_code == 0
        assert "saas-medium" in result.stdout

    def test_plan_shows_agents(self, monkeypatch: pytest.MonkeyPatch):
        """plan must list agent roles."""
        result = self.runner.invoke(app, ["plan", "Build a SaaS platform"], catch_exceptions=False)
        assert result.exit_code == 0
        assert "orchestrator" in result.stdout

    def test_plan_shows_task_dag(self, monkeypatch: pytest.MonkeyPatch):
        """plan must output a task DAG with steps."""
        result = self.runner.invoke(app, ["plan", "Build a SaaS platform"], catch_exceptions=False)
        assert result.exit_code == 0
        assert "step_" in result.stdout

    def test_plan_defaults_to_general_dev(self, monkeypatch: pytest.MonkeyPatch):
        """Unknown goal must fall back to general-dev."""
        result = self.runner.invoke(app, ["plan", "xyzzy_nonexistent_goal"], catch_exceptions=False)
        assert result.exit_code == 0
        assert "general-dev" in result.stdout


class TestPlanOutput:
    """Tests for plan YAML output."""

    runner = CliRunner()

    def test_plan_writes_yaml(self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch):
        """plan --output must write a valid YAML file."""
        monkeypatch.chdir(tmp_path)
        out_file = tmp_path / "plan.yaml"
        result = self.runner.invoke(
            app, ["plan", "Build a SaaS platform", "--output", str(out_file)],
            catch_exceptions=False,
        )
        assert result.exit_code == 0
        assert out_file.exists()
        plan = yaml.safe_load(out_file.read_text())
        assert "plan" in plan
        assert "agents" in plan["plan"]
        assert "task_dag" in plan["plan"]
