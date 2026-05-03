"""Tests: Agent lifecycle state management and volume lifecycle.

Uses mocked subprocess and file I/O to avoid requiring Docker.
"""
from __future__ import annotations

from pathlib import Path
from unittest.mock import MagicMock, mock_open, patch

import pytest
import yaml

from hermes_fleet.contracts import AgentState
from hermes_fleet.runner import (
    volume_restore,
    volume_snapshot,
    volume_wipe,
)


# ── AgentState Enum ──────────────────────────────────────────────────


class TestAgentState:
    def test_all_states_exist(self):
        states = [s.value for s in AgentState]
        assert states == ["created", "active", "idle", "completed", "archived"]

    def test_state_order(self):
        assert AgentState.CREATED.value == "created"
        assert AgentState.ACTIVE.value == "active"
        assert AgentState.IDLE.value == "idle"
        assert AgentState.COMPLETED.value == "completed"
        assert AgentState.ARCHIVED.value == "archived"

    def test_transition_from_created(self):
        assert AgentState.CREATED != AgentState.ACTIVE

    def test_idle_is_distinct(self):
        assert AgentState.IDLE not in (AgentState.ACTIVE, AgentState.COMPLETED)


# ── Volume Lifecycle (mocked subprocess) ──────────────────────────────


@pytest.fixture
def compose_file_content() -> str:
    return yaml.dump({
        "services": {
            "frontend-developer": {
                "container_name": "hermes-fleet-frontend-developer",
                "volumes": ["frontend-developer_data:/opt/data"],
                "image": "hermes-agent:latest",
            },
            "orchestrator": {
                "container_name": "hermes-fleet-orchestrator",
                "volumes": ["orchestrator_data:/opt/data"],
                "ports": ["127.0.0.1:8080:8080"],
            },
            "qa-tester": {
                "container_name": "hermes-fleet-qa-tester",
                "image": "hermes-agent:latest",
            },
        },
        "volumes": {
            "frontend-developer_data": {"driver": "local"},
            "orchestrator_data": {"driver": "local"},
        },
    })


@pytest.fixture
def project_dir(tmp_path: Path) -> Path:
    gen_dir = tmp_path / ".fleet" / "generated"
    gen_dir.mkdir(parents=True)
    return tmp_path


class TestVolumeWipe:
    @patch("hermes_fleet.runner.subprocess.run")
    def test_wipe_success(self, mock_run, project_dir, compose_file_content):
        compose_path = project_dir / ".fleet" / "generated" / "docker-compose.generated.yaml"
        compose_path.parent.mkdir(parents=True, exist_ok=True)
        compose_path.write_text(compose_file_content)

        mock_run.return_value = MagicMock(returncode=0, stdout="", stderr="")

        result = volume_wipe(project_dir, "frontend-developer")

        assert result["success"] is True
        assert "wiped" in result["message"]
        # Should have called docker stop, docker rm, docker volume rm
        assert mock_run.call_count >= 3

    @patch("hermes_fleet.runner.subprocess.run")
    def test_wipe_unknown_agent(self, mock_run, project_dir, compose_file_content):
        compose_path = project_dir / ".fleet" / "generated" / "docker-compose.generated.yaml"
        compose_path.parent.mkdir(parents=True, exist_ok=True)
        compose_path.write_text(compose_file_content)

        result = volume_wipe(project_dir, "nonexistent-agent")

        assert result["success"] is False
        assert "Unknown agent" in result["message"]

    def test_wipe_no_compose_file(self, project_dir):
        result = volume_wipe(project_dir, "frontend-developer")
        assert result["success"] is False
        assert "Compose file not found" in result["message"]

    @patch("hermes_fleet.runner.subprocess.run")
    def test_wipe_no_volumes_found(self, mock_run, project_dir, compose_file_content):
        compose_path = project_dir / ".fleet" / "generated" / "docker-compose.generated.yaml"
        compose_path.parent.mkdir(parents=True, exist_ok=True)
        compose_path.write_text(compose_file_content)

        result = volume_wipe(project_dir, "qa-tester")

        assert result["success"] is False
        assert "No data volumes" in result["message"]


class TestVolumeSnapshot:
    @patch("hermes_fleet.runner.subprocess.run")
    def test_snapshot_success(self, mock_run, project_dir, compose_file_content):
        compose_path = project_dir / ".fleet" / "generated" / "docker-compose.generated.yaml"
        compose_path.parent.mkdir(parents=True, exist_ok=True)
        compose_path.write_text(compose_file_content)

        mock_run.return_value = MagicMock(returncode=0, stdout="", stderr="")

        result = volume_snapshot(project_dir, "frontend-developer")

        assert result["success"] is True
        assert "Snapshot created" in result["message"]
        # Details should contain agent name and tar.gz extension
        assert "frontend-developer_" in result["details"]
        assert ".tar.gz" in result["details"]

    @patch("hermes_fleet.runner.subprocess.run")
    def test_snapshot_fails_docker(self, mock_run, project_dir, compose_file_content):
        compose_path = project_dir / ".fleet" / "generated" / "docker-compose.generated.yaml"
        compose_path.parent.mkdir(parents=True, exist_ok=True)
        compose_path.write_text(compose_file_content)

        mock_run.return_value = MagicMock(returncode=1, stdout="", stderr="docker error")

        result = volume_snapshot(project_dir, "frontend-developer")

        assert result["success"] is False
        assert "Snapshot failed" in result["message"]

    def test_snapshot_no_compose_file(self, project_dir):
        result = volume_snapshot(project_dir, "frontend-developer")
        assert result["success"] is False
        assert "Compose file not found" in result["message"]

    def test_snapshot_unknown_agent(self, project_dir, compose_file_content):
        compose_path = project_dir / ".fleet" / "generated" / "docker-compose.generated.yaml"
        compose_path.parent.mkdir(parents=True, exist_ok=True)
        compose_path.write_text(compose_file_content)

        result = volume_snapshot(project_dir, "nonexistent-agent")
        assert result["success"] is False
        assert "Unknown agent" in result["message"]


class TestVolumeRestore:
    @patch("hermes_fleet.runner.subprocess.run")
    def test_restore_success(self, mock_run, project_dir, compose_file_content):
        compose_path = project_dir / ".fleet" / "generated" / "docker-compose.generated.yaml"
        compose_path.parent.mkdir(parents=True, exist_ok=True)
        compose_path.write_text(compose_file_content)

        # Create snapshot file
        snap_dir = project_dir / ".fleet" / "snapshots"
        snap_dir.mkdir(parents=True)
        snapshot_file = snap_dir / "frontend-developer_20250101_120000.tar.gz"
        snapshot_file.write_text("dummy")

        mock_run.return_value = MagicMock(returncode=0, stdout="", stderr="")

        result = volume_restore(
            project_dir, "frontend-developer", "frontend-developer_20250101_120000.tar.gz"
        )

        assert result["success"] is True
        assert "Volume restored" in result["message"]

    def test_restore_no_compose_file(self, project_dir):
        result = volume_restore(
            project_dir, "frontend-developer", "snap.tar.gz"
        )
        assert result["success"] is False
        assert "Compose file not found" in result["message"]

    def test_restore_snapshot_not_found(self, project_dir, compose_file_content):
        compose_path = project_dir / ".fleet" / "generated" / "docker-compose.generated.yaml"
        compose_path.parent.mkdir(parents=True, exist_ok=True)
        compose_path.write_text(compose_file_content)

        result = volume_restore(
            project_dir, "frontend-developer", "nonexistent.tar.gz"
        )
        assert result["success"] is False
        assert "Snapshot not found" in result["message"]

    @patch("hermes_fleet.runner.subprocess.run")
    def test_restore_unknown_agent(self, mock_run, project_dir, compose_file_content):
        compose_path = project_dir / ".fleet" / "generated" / "docker-compose.generated.yaml"
        compose_path.parent.mkdir(parents=True, exist_ok=True)
        compose_path.write_text(compose_file_content)

        result = volume_restore(
            project_dir, "nonexistent-agent", "snap.tar.gz"
        )
        assert result["success"] is False
        assert "Unknown agent" in result["message"]


# ── _update_agent_state (mocked file I/O) ────────────────────────────


@pytest.fixture
def fleet_yaml_content() -> str:
    return yaml.dump({
        "fleet_version": "1.0",
        "name": "test-fleet",
        "team": "general-dev",
    })


class TestUpdateAgentState:
    def test_state_added_to_fleet_yaml(self, tmp_path):
        """Verify that _update_agent_state writes the correct structure."""
        from hermes_fleet.cli import _update_agent_state

        fleet_dir = tmp_path / ".fleet"
        fleet_dir.mkdir(parents=True)
        fleet_yaml = fleet_dir / "fleet.yaml"

        initial = {"fleet_version": "1.0", "name": "test"}
        fleet_yaml.write_text(yaml.dump(initial))

        # We patch Path.cwd() to return tmp_path so fleet_yaml resolves correctly
        original_cwd = Path.cwd
        try:
            # Temporarily change cwd
            import os
            original_dir = os.getcwd()
            os.chdir(str(tmp_path))

            result = _update_agent_state("frontend-developer", "idle")
            assert result is True

            with open(fleet_yaml) as f:
                config = yaml.safe_load(f)
            assert config["agent_states"]["frontend-developer"]["state"] == "idle"
        finally:
            os.chdir(original_dir)

    def test_state_overwrites_previous(self, tmp_path):
        from hermes_fleet.cli import _update_agent_state

        fleet_dir = tmp_path / ".fleet"
        fleet_dir.mkdir(parents=True)
        fleet_yaml = fleet_dir / "fleet.yaml"

        initial = {
            "fleet_version": "1.0",
            "agent_states": {"frontend-developer": {"state": "active"}},
        }
        fleet_yaml.write_text(yaml.dump(initial))

        import os
        original_dir = os.getcwd()
        try:
            os.chdir(str(tmp_path))
            _update_agent_state("frontend-developer", "idle")

            with open(fleet_yaml) as f:
                config = yaml.safe_load(f)
            assert config["agent_states"]["frontend-developer"]["state"] == "idle"
        finally:
            os.chdir(original_dir)
