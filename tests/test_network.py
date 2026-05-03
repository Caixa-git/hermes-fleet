"""Tests: Network policy resolution and isolation modes.

Pure data tests -- no Docker, no file I/O.
"""
from __future__ import annotations

from datetime import datetime, timedelta

from hermes_fleet.network import (
    INTERNET_ACCESS,
    NETWORK_MAP,
    ROLE_DEFAULT_NETWORK,
    NetworkMode,
    TempAccessRequest,
    get_token_budget,
    resolve_network_mode,
    select_networks,
    should_publish_ports,
)


# ── Enum ────────────────────────────────────────────────────────────────


class TestNetworkMode:
    def test_values(self):
        assert NetworkMode.ISOLATED.value == "isolated"
        assert NetworkMode.CONTROL_PLANE.value == "control-plane"
        assert NetworkMode.PROXY.value == "proxy"
        assert NetworkMode.EXTERN.value == "extern"

    def test_all_modes_covered_by_map(self):
        for mode in NetworkMode:
            assert mode in NETWORK_MAP

    def test_all_modes_have_internet_flag(self):
        for mode in NetworkMode:
            assert mode in INTERNET_ACCESS


# ── NETWORK_MAP ─────────────────────────────────────────────────────────


class TestNetworkMap:
    def test_isolated_network(self):
        assert NETWORK_MAP[NetworkMode.ISOLATED] == "fleet-no-net"

    def test_control_plane_network(self):
        assert NETWORK_MAP[NetworkMode.CONTROL_PLANE] == "fleet-control-plane"

    def test_proxy_network(self):
        assert NETWORK_MAP[NetworkMode.PROXY] == "fleet-control-plane"

    def test_extern_network(self):
        assert NETWORK_MAP[NetworkMode.EXTERN] == "fleet-web"


# ── INTERNET_ACCESS ─────────────────────────────────────────────────────


class TestInternetAccess:
    def test_isolated_no_internet(self):
        assert INTERNET_ACCESS[NetworkMode.ISOLATED] is False

    def test_control_plane_no_internet(self):
        assert INTERNET_ACCESS[NetworkMode.CONTROL_PLANE] is False

    def test_proxy_has_internet(self):
        assert INTERNET_ACCESS[NetworkMode.PROXY] is True

    def test_extern_has_internet(self):
        assert INTERNET_ACCESS[NetworkMode.EXTERN] is True


# ── ROLE_DEFAULT_NETWORK ────────────────────────────────────────────────


class TestRoleDefaultNetwork:
    def test_security_reviewer_isolated(self):
        assert ROLE_DEFAULT_NETWORK["security-reviewer"] == "isolated"

    def test_orchestrator_control_plane(self):
        assert ROLE_DEFAULT_NETWORK["orchestrator"] == "control-plane"

    def test_frontend_dev_proxy(self):
        assert ROLE_DEFAULT_NETWORK["frontend-developer"] == "proxy"

    def test_devops_extern(self):
        assert ROLE_DEFAULT_NETWORK["devops"] == "extern"

    def test_all_roles_have_default(self):
        essential = {
            "security-reviewer", "qa-tester", "technical-writer",
            "product-manager", "ux-designer", "code-reviewer",
            "frontend-developer", "backend-developer", "database-architect",
            "devops", "orchestrator",
        }
        assert essential.issubset(ROLE_DEFAULT_NETWORK.keys())


# ── resolve_network_mode ────────────────────────────────────────────────


class TestResolveNetworkMode:
    def test_per_agent_override(self):
        result = resolve_network_mode(
            "frontend-developer",
            {"default": "isolated", "per_agent": {"frontend-developer": "extern"}},
        )
        assert result == "extern"

    def test_fleet_default(self):
        result = resolve_network_mode(
            "frontend-developer",
            {"default": "extern"},
        )
        assert result == "extern"

    def test_role_default_when_no_policy(self):
        result = resolve_network_mode("frontend-developer")
        assert result == "proxy"

    def test_role_default_when_empty_policy(self):
        result = resolve_network_mode("frontend-developer", {})
        assert result == "proxy"

    def test_global_default_for_unknown_role(self):
        result = resolve_network_mode("unknown-role")
        assert result == "isolated"

    def test_unknown_role_with_empty_policy(self):
        result = resolve_network_mode("unknown-role", {})
        assert result == "isolated"

    def test_orchestrator_default(self):
        result = resolve_network_mode("orchestrator")
        assert result == "control-plane"


# ── select_networks ─────────────────────────────────────────────────────


class TestSelectNetworks:
    def test_isolated(self):
        assert select_networks("isolated") == ["fleet-no-net"]

    def test_control_plane(self):
        assert select_networks("control-plane") == ["fleet-control-plane"]

    def test_proxy(self):
        assert select_networks("proxy") == ["fleet-control-plane"]

    def test_extern(self):
        assert select_networks("extern") == ["fleet-web"]

    def test_invalid_mode_falls_back_to_isolated(self):
        assert select_networks("invalid") == ["fleet-no-net"]

    def test_empty_mode_falls_back(self):
        assert select_networks("") == ["fleet-no-net"]


# ── should_publish_ports ────────────────────────────────────────────────


class TestShouldPublishPorts:
    def test_orchestrator_always_publishes(self):
        assert should_publish_ports("isolated", "orchestrator") is True

    def test_extern_mode_publishes(self):
        assert should_publish_ports("extern", "backend-developer") is True

    def test_isolated_does_not_publish(self):
        assert should_publish_ports("isolated", "security-reviewer") is False

    def test_control_plane_does_not_publish(self):
        assert should_publish_ports("control-plane", "code-reviewer") is False

    def test_proxy_does_not_publish(self):
        assert should_publish_ports("proxy", "frontend-developer") is False


# ── get_token_budget ────────────────────────────────────────────────────


class TestGetTokenBudget:
    def test_per_agent_override(self):
        result = get_token_budget(
            "orchestrator",
            {"default": 50, "per_agent": {"orchestrator": 200}},
        )
        assert result == 200

    def test_fleet_default(self):
        result = get_token_budget(
            "frontend-developer",
            {"default": 100},
        )
        assert result == 100

    def test_global_default_when_no_policy(self):
        result = get_token_budget("frontend-developer")
        assert result == 50

    def test_global_default_when_empty_policy(self):
        result = get_token_budget("frontend-developer", {})
        assert result == 50

    def test_unknown_agent_gets_default(self):
        result = get_token_budget("unknown-agent", {"default": 75})
        assert result == 75


# ── TempAccessRequest ───────────────────────────────────────────────────


class TestTempAccessRequest:
    def test_default_expires_at_15_minutes(self):
        req = TempAccessRequest(agent_id="frontend-dev", target="pypi.org:443", reason="need pip install")
        expected = req.created_at + timedelta(minutes=15)
        assert abs((req.expires_at - expected).total_seconds()) < 1

    def test_custom_duration(self):
        req = TempAccessRequest(
            agent_id="frontend-dev", target="npmjs.org:443", duration_minutes=30,
            reason="need npm install",
        )
        expected = req.created_at + timedelta(minutes=30)
        assert abs((req.expires_at - expected).total_seconds()) < 1

    def test_not_expired_when_recent(self):
        req = TempAccessRequest(agent_id="dev", target="example.com:443", reason="testing")
        assert req.is_expired is False

    def test_expired_when_past_expiry(self):
        req = TempAccessRequest(
            agent_id="dev", target="example.com:443",
            created_at=datetime(2020, 1, 1),
            reason="testing",
        )
        assert req.is_expired is True

    def test_not_active_when_not_approved(self):
        req = TempAccessRequest(agent_id="dev", target="example.com:443", reason="testing")
        assert req.is_active is False

    def test_active_when_approved_and_not_expired(self):
        req = TempAccessRequest(
            agent_id="dev", target="example.com:443",
            created_at=datetime.now(),
            approved=True, approved_by="user",
            reason="testing",
        )
        assert req.is_active is True

    def test_not_active_when_expired_even_if_approved(self):
        req = TempAccessRequest(
            agent_id="dev", target="example.com:443",
            created_at=datetime(2020, 1, 1),
            approved=True, approved_by="user",
            reason="testing",
        )
        assert req.is_active is False

    def test_explicit_expires_at(self):
        future = datetime.now() + timedelta(hours=2)
        req = TempAccessRequest(
            agent_id="dev", target="example.com:443",
            expires_at=future,
            reason="testing",
        )
        assert req.expires_at == future
