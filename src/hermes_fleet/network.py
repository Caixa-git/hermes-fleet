"""Network policy resolution and temporary access management.

Defines how network isolation modes map to Docker Compose
network configurations, and provides infrastructure for
temporary network access requests (orchestrator integration
will use this in v0.5).
"""

from __future__ import annotations

import enum
from dataclasses import dataclass, field
from datetime import datetime, timedelta
from typing import Any


class NetworkMode(str, enum.Enum):
    """Four network isolation modes for agents."""

    ISOLATED = "isolated"
    CONTROL_PLANE = "control-plane"
    PROXY = "proxy"
    EXTERN = "extern"


# Docker Compose network name mapping
NETWORK_MAP: dict[NetworkMode, str] = {
    NetworkMode.ISOLATED: "fleet-no-net",
    NetworkMode.CONTROL_PLANE: "fleet-control-plane",
    NetworkMode.PROXY: "fleet-control-plane",
    NetworkMode.EXTERN: "fleet-web",
}

# Whether the mode allows outbound internet access
INTERNET_ACCESS: dict[NetworkMode, bool] = {
    NetworkMode.ISOLATED: False,
    NetworkMode.CONTROL_PLANE: False,
    NetworkMode.PROXY: True,  # via orchestrator proxy
    NetworkMode.EXTERN: True,
}

# Default network mode by role
ROLE_DEFAULT_NETWORK: dict[str, str] = {
    "security-reviewer": "isolated",
    "qa-tester": "isolated",
    "technical-writer": "isolated",
    "product-manager": "isolated",
    "ux-designer": "isolated",
    "code-reviewer": "control-plane",
    "frontend-developer": "proxy",
    "backend-developer": "proxy",
    "database-architect": "proxy",
    "devops": "extern",
    "orchestrator": "control-plane",
}


@dataclass
class TempAccessRequest:
    """A temporary network access request from an agent."""

    agent_id: str
    target: str  # e.g. "registry.npmjs.org:443"
    reason: str
    duration_minutes: int = 15
    created_at: datetime = field(default_factory=datetime.now)
    expires_at: datetime | None = None
    approved: bool = False
    approved_by: str | None = None  # "user" or "orchestrator"

    def __post_init__(self) -> None:
        if self.expires_at is None:
            self.expires_at = self.created_at + timedelta(minutes=self.duration_minutes)

    @property
    def is_expired(self) -> bool:
        if self.expires_at is None:
            return False
        return datetime.now() > self.expires_at

    @property
    def is_active(self) -> bool:
        return self.approved and not self.is_expired


def resolve_network_mode(
    agent_id: str,
    fleet_network_policy: dict[str, Any] | None = None,
) -> str:
    """Resolve the network mode for an agent.

    Resolution order:
    1. fleet.yaml's per_agent override (e.g. {agent_id: "proxy"})
    2. fleet.yaml's default mode
    3. Role-specific default
    4. Global default ("isolated")

    Args:
        agent_id: The agent's role/ID.
        fleet_network_policy: Optional dict from fleet.yaml's network_policy field.
            Expected format: {"default": "isolated", "per_agent": {...}}.

    Returns:
        One of: "isolated", "control-plane", "proxy", "extern".
    """
    if fleet_network_policy:
        # Per-agent override
        per_agent = fleet_network_policy.get("per_agent", {})
        if isinstance(per_agent, dict) and agent_id in per_agent:
            return per_agent[agent_id]

        # Fleet default
        default = fleet_network_policy.get("default", "")
        if default:
            return default

    # Role-specific default
    role_default = ROLE_DEFAULT_NETWORK.get(agent_id)
    if role_default:
        return role_default

    # Global default
    return "isolated"


def select_networks(mode: str) -> list[str]:
    """Select Docker Compose networks based on network mode.

    Args:
        mode: One of "isolated", "control-plane", "proxy", "extern".

    Returns:
        List of Docker Compose network names.
    """
    try:
        nm = NetworkMode(mode)
        return [NETWORK_MAP[nm]]
    except ValueError:
        return [NETWORK_MAP[NetworkMode.ISOLATED]]


def should_publish_ports(mode: str, agent_id: str) -> bool:
    """Whether this agent's gateway ports should be published.

    Only the orchestrator and extern-mode agents get published ports.
    All other agents are unreachable from outside Docker.
    """
    if agent_id == "orchestrator":
        return True
    return mode == "extern"


def get_token_budget(
    agent_id: str,
    fleet_token_budget: dict[str, Any] | None = None,
) -> int:
    """Resolve the token budget for an agent.

    Resolution order:
    1. fleet.yaml's per_agent override
    2. fleet.yaml's default
    3. Global default (50)

    Args:
        agent_id: The agent's role/ID.
        fleet_token_budget: Optional dict from fleet.yaml's token_budget field.
            Expected format: {"default": 50, "per_agent": {...}}.

    Returns:
        Token budget as int.
    """
    if fleet_token_budget:
        per_agent = fleet_token_budget.get("per_agent", {})
        if isinstance(per_agent, dict) and agent_id in per_agent:
            return int(per_agent[agent_id])
        default = fleet_token_budget.get("default", 50)
        return int(default)
    return 50
