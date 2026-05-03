"""
Tests: Fleet runner (Docker lifecycle operations).

Uses mock subprocess to avoid requiring Docker during unit tests.
"""

from __future__ import annotations

from pathlib import Path
from unittest.mock import patch, MagicMock

import pytest
import yaml

from hermes_fleet.runner import (
    DockerNotAvailableError,
    up,
    down,
    status,
    logs,
    restart,
    _check_docker,
    _get_container_name,
)


class TestCheckDocker:
    """_check_docker() availability check."""

    @patch("hermes_fleet.runner.subprocess.run")
    def test_docker_available(self, mock_run):
        mock_run.return_value = MagicMock(
            returncode=0, stdout="Docker version 24.0.7\n"
        )
        version = _check_docker()
        assert "Docker" in version

    @patch("hermes_fleet.runner.subprocess.run")
    def test_docker_not_available_raises(self, mock_run):
        mock_run.return_value = MagicMock(returncode=1, stdout="", stderr="not found")
        mock_run.side_effect = FileNotFoundError()
        with pytest.raises(DockerNotAvailableError):
            _check_docker()

    @patch("hermes_fleet.runner.subprocess.run")
    def test_docker_bad_returncode_raises(self, mock_run):
        mock_run.return_value = MagicMock(returncode=1, stdout="", stderr="error")
        with pytest.raises(DockerNotAvailableError):
            _check_docker()


class TestGetContainerName:
    """_get_container_name() compose file parsing."""

    @pytest.fixture
    def project_dir(self, tmp_path) -> Path:
        fleet_dir = tmp_path / ".fleet" / "generated"
        fleet_dir.mkdir(parents=True)
        compose = {
            "services": {
                "orchestrator": {
                    "container_name": "hermes-fleet-orchestrator-test",
                    "image": "test:latest",
                },
                "reviewer": {
                    "container_name": "hermes-fleet-reviewer-test",
                },
            }
        }
        compose_file = fleet_dir / "docker-compose.generated.yaml"
        with open(compose_file, "w") as f:
            yaml.dump(compose, f)
        return tmp_path

    def test_finds_existing_service(self, project_dir):
        name = _get_container_name(project_dir, "orchestrator")
        assert name == "hermes-fleet-orchestrator-test"

    def test_unknown_service_returns_none(self, project_dir):
        name = _get_container_name(project_dir, "nonexistent")
        assert name is None

    def test_no_compose_file_returns_none(self, tmp_path):
        name = _get_container_name(tmp_path, "orchestrator")
        assert name is None


class TestUp:
    """hermes-fleet up"""

    @patch("hermes_fleet.runner._compose_cmd")
    @patch("hermes_fleet.runner._check_docker")
    def test_up_success(self, mock_check, mock_compose):
        mock_check.return_value = "Docker 24.0"
        mock_compose.return_value = MagicMock(
            returncode=0, stdout="Container started", stderr=""
        )
        result = up(Path("/test"))
        assert result["success"] is True
        assert "started" in result["message"].lower()

    @patch("hermes_fleet.runner._check_docker")
    def test_up_docker_unavailable(self, mock_check):
        mock_check.side_effect = DockerNotAvailableError("Docker not found")
        result = up(Path("/test"))
        assert result["success"] is False
        assert "not found" in result["message"].lower()

    @patch("hermes_fleet.runner._compose_cmd")
    @patch("hermes_fleet.runner._check_docker")
    def test_up_compose_fails(self, mock_check, mock_compose):
        mock_check.return_value = "Docker 24.0"
        mock_compose.return_value = MagicMock(
            returncode=1, stdout="", stderr="error: context canceled"
        )
        result = up(Path("/test"))
        assert result["success"] is False


class TestDown:
    """hermes-fleet down"""

    @patch("hermes_fleet.runner._compose_cmd")
    @patch("hermes_fleet.runner._check_docker")
    def test_down_success(self, mock_check, mock_compose):
        mock_check.return_value = "Docker 24.0"
        mock_compose.return_value = MagicMock(
            returncode=0, stdout="Stopped", stderr=""
        )
        result = down(Path("/test"))
        assert result["success"] is True
        assert "stopped" in result["message"].lower()

    @patch("hermes_fleet.runner._compose_cmd")
    @patch("hermes_fleet.runner._check_docker")
    def test_down_with_volumes(self, mock_check, mock_compose):
        mock_check.return_value = "Docker 24.0"
        mock_compose.return_value = MagicMock(returncode=0, stdout="", stderr="")
        result = down(Path("/test"), remove_volumes=True)
        assert result["success"] is True
        # verify -v was passed (indirectly via compose cmd)
        assert mock_compose.called


class TestStatus:
    """hermes-fleet status"""

    @patch("hermes_fleet.runner._compose_cmd")
    @patch("hermes_fleet.runner._check_docker")
    def test_status_all_running(self, mock_check, mock_compose):
        mock_check.return_value = "Docker 24.0"
        mock_compose.return_value = MagicMock(
            returncode=0,
            stdout='{"Name":"hermes-fleet-orchestrator","State":"running","Status":"Up 2m"}\n'
                   '{"Name":"hermes-fleet-reviewer","State":"running","Status":"Up 1m"}',
            stderr="",
        )
        result = status(Path("/test"))
        assert result["success"] is True
        assert result["message"] == "2/2 containers running"
        assert len(result["containers"]) == 2
        assert all(c["state"] == "running" for c in result["containers"])

    @patch("hermes_fleet.runner._compose_cmd")
    @patch("hermes_fleet.runner._check_docker")
    def test_status_some_stopped(self, mock_check, mock_compose):
        mock_check.return_value = "Docker 24.0"
        mock_compose.return_value = MagicMock(
            returncode=0,
            stdout='{"Name":"hermes-fleet-orchestrator","State":"running","Status":"Up 5m"}\n'
                   '{"Name":"hermes-fleet-reviewer","State":"exited","Status":"Exited (1) 10s ago"}',
            stderr="",
        )
        result = status(Path("/test"))
        assert result["containers"][1]["state"] == "exited"

    @patch("hermes_fleet.runner._compose_cmd")
    @patch("hermes_fleet.runner._check_docker")
    def test_status_empty_output(self, mock_check, mock_compose):
        mock_check.return_value = "Docker 24.0"
        mock_compose.return_value = MagicMock(
            returncode=0, stdout="", stderr=""
        )
        result = status(Path("/test"))
        assert result["containers"] == []

    @patch("hermes_fleet.runner._check_docker")
    def test_status_no_docker(self, mock_check):
        mock_check.side_effect = DockerNotAvailableError("no docker")
        result = status(Path("/test"))
        assert result["containers"] == []


class TestLogs:
    """hermes-fleet logs"""

    @patch("hermes_fleet.runner.subprocess.run")
    @patch("hermes_fleet.runner._get_container_name")
    @patch("hermes_fleet.runner._check_docker")
    def test_logs_success(self, mock_check, mock_get_name, mock_run):
        mock_check.return_value = "Docker 24.0"
        mock_get_name.return_value = "hermes-fleet-orchestrator-test"
        mock_run.return_value = MagicMock(
            returncode=0, stdout="[INFO] Agent started\n[INFO] Processing task\n", stderr=""
        )
        result = logs(Path("/test"), "orchestrator")
        assert result["success"] is True
        assert "Agent started" in result["logs"]

    @patch("hermes_fleet.runner._get_container_name")
    @patch("hermes_fleet.runner._check_docker")
    def test_logs_unknown_agent(self, mock_check, mock_get_name):
        mock_check.return_value = "Docker 24.0"
        mock_get_name.return_value = None
        result = logs(Path("/test"), "nonexistent")
        assert result["success"] is False
        assert "Unknown" in result["message"]

    @patch("hermes_fleet.runner.subprocess.run")
    @patch("hermes_fleet.runner._get_container_name")
    @patch("hermes_fleet.runner._check_docker")
    def test_logs_container_not_found(self, mock_check, mock_get_name, mock_run):
        mock_check.return_value = "Docker 24.0"
        mock_get_name.return_value = "hermes-fleet-ghost"
        mock_run.return_value = MagicMock(
            returncode=1, stdout="", stderr="Error: No such container"
        )
        result = logs(Path("/test"), "ghost")
        assert result["success"] is False


class TestRestart:
    """hermes-fleet restart"""

    @patch("hermes_fleet.runner._compose_cmd")
    @patch("hermes_fleet.runner._get_container_name")
    @patch("hermes_fleet.runner._check_docker")
    def test_restart_success(self, mock_check, mock_get_name, mock_compose):
        mock_check.return_value = "Docker 24.0"
        mock_get_name.return_value = "hermes-fleet-orchestrator-test"
        mock_compose.return_value = MagicMock(returncode=0, stdout="Restarted", stderr="")
        result = restart(Path("/test"), "orchestrator")
        assert result["success"] is True
        assert "restarted" in result["message"].lower()

    @patch("hermes_fleet.runner._get_container_name")
    @patch("hermes_fleet.runner._check_docker")
    def test_restart_unknown_agent(self, mock_check, mock_get_name):
        mock_check.return_value = "Docker 24.0"
        mock_get_name.return_value = None
        result = restart(Path("/test"), "ghost")
        assert result["success"] is False
        assert "Unknown" in result["message"]


class TestComposeFileNotFound:
    """Error handling when compose file doesn't exist."""

    @patch("hermes_fleet.runner._check_docker")
    def test_up_no_compose_file(self, mock_check, tmp_path):
        mock_check.return_value = "Docker 24.0"
        result = up(tmp_path)
        assert result["success"] is False
        assert "not found" in result["message"].lower()

    @patch("hermes_fleet.runner._check_docker")
    def test_down_no_compose_file(self, mock_check, tmp_path):
        mock_check.return_value = "Docker 24.0"
        result = down(tmp_path)
        assert result["success"] is False
        assert "not found" in result["message"].lower()
