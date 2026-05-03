"""
Tests: Docker Compose generation and security defaults.
"""

from pathlib import Path

import pytest
import yaml

from hermes_fleet.docker_compose import generate_docker_compose
from hermes_fleet.teams import load_team


class TestDockerComposeGeneration:
    """Tests for Docker Compose file generation."""

    @pytest.fixture
    def general_dev_compose(self):
        team = load_team("general-dev")
        assert team is not None
        return generate_docker_compose("general-dev", team["agents"])

    @pytest.fixture
    def saas_medium_compose(self):
        team = load_team("saas-medium")
        assert team is not None
        return generate_docker_compose("saas-medium", team["agents"])

    def test_docker_compose_is_valid_yaml(self, general_dev_compose):
        yaml_str = yaml.dump(general_dev_compose, default_flow_style=False)
        reloaded = yaml.safe_load(yaml_str)
        assert reloaded is not None
        assert "services" in reloaded
        assert "volumes" in reloaded
        assert "networks" in reloaded

    def test_every_agent_has_service(self, general_dev_compose, saas_medium_compose):
        team = load_team("general-dev")
        services = general_dev_compose.get("services", {})
        for agent_id in team["agents"]:
            assert agent_id in services, f"Agent '{agent_id}' missing from Docker Compose"

        team_saas = load_team("saas-medium")
        services_saas = saas_medium_compose.get("services", {})
        for agent_id in team_saas["agents"]:
            assert agent_id in services_saas, f"Agent '{agent_id}' missing from Docker Compose"

    def test_no_privileged_containers(self, general_dev_compose):
        for svc_name, svc in general_dev_compose.get("services", {}).items():
            assert svc.get("privileged") is not True, f"Service '{svc_name}' has privileged: true"

    def test_no_docker_sock_mounts(self, general_dev_compose):
        for svc_name, svc in general_dev_compose.get("services", {}).items():
            volumes = svc.get("volumes", [])
            for vol in volumes:
                if isinstance(vol, dict):
                    src = vol.get("source", "")
                else:
                    src = str(vol).split(":")[0] if ":" in str(vol) else ""
                assert "docker.sock" not in src, (
                    f"Service '{svc_name}' mounts docker socket"
                )
                assert "/var/run/docker" not in src, (
                    f"Service '{svc_name}' mounts docker socket path"
                )

    def test_no_host_network_mode(self, general_dev_compose):
        for svc_name, svc in general_dev_compose.get("services", {}).items():
            assert svc.get("network_mode") != "host", (
                f"Service '{svc_name}' uses host network mode"
            )

    def test_all_services_have_cap_drop_all(self, general_dev_compose):
        for svc_name, svc in general_dev_compose.get("services", {}).items():
            caps = svc.get("cap_drop", [])
            assert "ALL" in caps, f"Service '{svc_name}' missing cap_drop: [ALL]"

    def test_all_services_have_no_new_privileges(self, general_dev_compose):
        for svc_name, svc in general_dev_compose.get("services", {}).items():
            sec_opt = svc.get("security_opt", [])
            assert any("no-new-privileges" in opt for opt in sec_opt), (
                f"Service '{svc_name}' missing no-new-privileges"
            )

    def test_all_services_have_pids_limit(self, general_dev_compose):
        for svc_name, svc in general_dev_compose.get("services", {}).items():
            assert svc.get("pids_limit") is not None, (
                f"Service '{svc_name}' missing pids_limit"
            )

    def test_all_services_have_read_only_root(self, general_dev_compose):
        for svc_name, svc in general_dev_compose.get("services", {}).items():
            assert svc.get("read_only") is True, (
                f"Service '{svc_name}' missing read_only: true"
            )

    def test_all_services_have_tmpfs(self, general_dev_compose):
        for svc_name, svc in general_dev_compose.get("services", {}).items():
            tmpfs = svc.get("tmpfs", [])
            assert len(tmpfs) >= 2, f"Service '{svc_name}' missing tmpfs mounts"
            assert any("/tmp" in t for t in tmpfs), f"Service '{svc_name}' missing /tmp tmpfs"
            assert any("/run" in t for t in tmpfs), f"Service '{svc_name}' missing /run tmpfs"

    def test_every_agent_has_separate_opt_data_volume(self, general_dev_compose):
        """Every agent must have its own named volume for /opt/data."""
        services = general_dev_compose.get("services", {})
        volumes = general_dev_compose.get("volumes", {})
        for svc_name, svc in services.items():
            svc_volumes = svc.get("volumes", [])
            has_data_vol = False
            for vol in svc_volumes:
                if isinstance(vol, str):
                    if "_data:" in vol and "/opt/data" in vol:
                        has_data_vol = True
                        vol_name = vol.split(":")[0]
                        assert vol_name in volumes, f"Volume '{vol_name}' not declared"
                elif isinstance(vol, dict):
                    if "/opt/data" in vol.get("target", ""):
                        has_data_vol = True
            assert has_data_vol, f"Service '{svc_name}' missing /opt/data volume"

    def test_resource_limits_set(self, general_dev_compose):
        for svc_name, svc in general_dev_compose.get("services", {}).items():
            deploy = svc.get("deploy", {})
            resources = deploy.get("resources", {})
            limits = resources.get("limits", {})
            assert "cpus" in limits, f"Service '{svc_name}' missing CPU limit"
            assert "memory" in limits, f"Service '{svc_name}' missing memory limit"

    def test_docker_compose_yaml_roundtrip(self, general_dev_compose):
        """Generated compose must be deterministic."""
        yaml_str1 = yaml.dump(general_dev_compose, default_flow_style=False)
        yaml_str2 = yaml.dump(general_dev_compose, default_flow_style=False)
        assert yaml_str1 == yaml_str2, "Docker Compose output is not deterministic"
