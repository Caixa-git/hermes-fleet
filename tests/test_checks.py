"""
Tests: Reusable check functions.

Tests the pure validation functions in hermes_fleet.checks.
No file I/O, no real Docker, no Hermes agent execution.
"""

import pytest

from hermes_fleet.checks import (
    check_no_privileged_containers,
    check_no_docker_sock_mounts,
    check_no_host_network_mode,
    check_all_services_have_cap_drop_all,
    check_all_services_have_no_new_privileges,
    check_all_services_have_pids_limit,
    check_all_services_have_read_only_root,
    run_docker_compose_checks,
)


def _make_service(overrides: dict = None) -> dict:
    """Create a minimal valid service dict."""
    svc = {
        "image": "test:latest",
        "cap_drop": ["ALL"],
        "security_opt": ["no-new-privileges:true"],
        "pids_limit": 256,
        "read_only": True,
        "volumes": [],
    }
    if overrides:
        svc.update(overrides)
    return svc


def _make_compose(services: dict = None) -> dict:
    """Create a minimal valid compose dict."""
    return {
        "services": services or {"test-svc": _make_service()},
        "volumes": {},
        "networks": {},
    }


class TestCheckNoPrivilegedContainers:
    def test_no_privileged_passes(self):
        compose = _make_compose()
        result = check_no_privileged_containers(compose)
        assert result["status"] == "passed"

    def test_privileged_fails(self):
        compose = _make_compose({"svc": _make_service({"privileged": True})})
        result = check_no_privileged_containers(compose)
        assert result["status"] == "failed"
        assert "privileged" in result["message"].lower()


class TestCheckNoDockerSockMounts:
    def test_no_sock_passes(self):
        compose = _make_compose()
        result = check_no_docker_sock_mounts(compose)
        assert result["status"] == "passed"

    def test_docker_sock_fails(self):
        compose = _make_compose({
            "svc": _make_service({"volumes": ["/var/run/docker.sock:/var/run/docker.sock"]})
        })
        result = check_no_docker_sock_mounts(compose)
        assert result["status"] == "failed"
        assert "docker.sock" in result["message"].lower()


class TestCheckNoHostNetworkMode:
    def test_no_host_network_passes(self):
        result = check_no_host_network_mode(_make_compose())
        assert result["status"] == "passed"

    def test_host_network_fails(self):
        compose = _make_compose({"svc": _make_service({"network_mode": "host"})})
        result = check_no_host_network_mode(compose)
        assert result["status"] == "failed"


class TestCheckCapDropAll:
    def test_cap_drop_all_passes(self):
        result = check_all_services_have_cap_drop_all(_make_compose())
        assert result["status"] == "passed"

    def test_missing_cap_drop_fails(self):
        compose = _make_compose({"svc": _make_service({"cap_drop": []})})
        result = check_all_services_have_cap_drop_all(compose)
        assert result["status"] == "failed"


class TestCheckNoNewPrivileges:
    def test_no_new_privs_passes(self):
        result = check_all_services_have_no_new_privileges(_make_compose())
        assert result["status"] == "passed"

    def test_missing_no_new_privs_fails(self):
        compose = _make_compose({"svc": _make_service({"security_opt": []})})
        result = check_all_services_have_no_new_privileges(compose)
        assert result["status"] == "failed"


class TestCheckPidsLimit:
    def test_pids_limit_passes(self):
        result = check_all_services_have_pids_limit(_make_compose())
        assert result["status"] == "passed"

    def test_missing_pids_limit_fails(self):
        compose = _make_compose({"svc": _make_service({"pids_limit": None})})
        result = check_all_services_have_pids_limit(compose)
        assert result["status"] == "failed"


class TestCheckReadOnlyRoot:
    def test_read_only_passes(self):
        result = check_all_services_have_read_only_root(_make_compose())
        assert result["status"] == "passed"

    def test_read_only_false_fails(self):
        compose = _make_compose({"svc": _make_service({"read_only": False})})
        result = check_all_services_have_read_only_root(compose)
        assert result["status"] == "failed"


class TestRunDockerComposeChecks:
    def test_all_checks_run(self):
        """run_docker_compose_checks should return at least 1 result."""
        compose = _make_compose()
        results = run_docker_compose_checks(compose)
        assert len(results) >= 1

    def test_all_pass_for_valid_compose(self):
        compose = _make_compose()
        results = run_docker_compose_checks(compose)
        for r in results:
            assert r["status"] == "passed", f"Check {r['check']} failed: {r['message']}"

    def test_all_have_check_names(self):
        compose = _make_compose()
        results = run_docker_compose_checks(compose)
        for r in results:
            assert r["check"], f"Missing check name in result: {r}"
