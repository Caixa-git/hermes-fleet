"""Pydantic contracts for Hermes Fleet configuration validation."""

from __future__ import annotations

import enum
from typing import Any

from pydantic import BaseModel, field_validator


class ContractValidationError(Exception):
    """Raised when a contract fails validation."""


# ── Permission Preset ──────────────────────────────────────────────────────────


class PermissionPresetContract(BaseModel):
    """Contract for permission preset YAML files."""

    preset_id: str
    workspace: str
    repo_write: bool
    secrets: str | list[str]
    network: str

    @field_validator("preset_id")
    @classmethod
    def preset_id_not_empty(cls, v: str) -> str:
        if not v.strip():
            raise ValueError("preset_id must not be empty")
        return v.strip()


def permission_preset_from_dict(data: dict[str, Any]) -> PermissionPresetContract:
    """Convert a raw dict (from YAML) to a PermissionPresetContract."""
    return PermissionPresetContract(
        preset_id=data.get("preset_id", data.get("id", "")),
        workspace=data.get("workspace", ""),
        repo_write=data.get("repo_write", False),
        secrets=data.get("secrets", []),
        network=data.get("network", ""),
    )


# ── Team ───────────────────────────────────────────────────────────────────────


class TeamContract(BaseModel):
    """Contract for team YAML files."""

    id: str
    name: str
    agents: list[str]
    optional_agents: list[str] = []

    @field_validator("id")
    @classmethod
    def id_not_empty(cls, v: str) -> str:
        if not v.strip():
            raise ValueError("team id must not be empty")
        return v.strip()

    @field_validator("agents")
    @classmethod
    def agents_not_empty(cls, v: list[str]) -> list[str]:
        if not v:
            raise ValueError("team must have at least one agent")
        return v


def team_from_dict(data: dict[str, Any]) -> TeamContract:
    """Convert a raw dict (from YAML) to a TeamContract.

    Handles both list and dict formats for optional_agents.
    Dict format: {agent_id: enabled_bool} -> extracts keys.
    """
    optional = data.get("optional_agents", data.get("optional", {}))
    if isinstance(optional, dict):
        optional_list = list(optional.keys())
    elif isinstance(optional, list):
        optional_list = optional
    else:
        optional_list = []
    return TeamContract(
        id=data.get("id", data.get("team", "")),
        name=data.get("name", data.get("id", "")),
        agents=data.get("agents", data.get("members", [])),
        optional_agents=optional_list,
    )


# ── Role ───────────────────────────────────────────────────────────────────────


class RoleContract(BaseModel):
    """Contract for role YAML files."""

    id: str
    name: str
    description: str
    mission: str
    non_goals: str = ""
    permission_preset: str
    allowed_tasks: list[str] = []
    forbidden_tasks: list[str] = []
    allowed_commands: list[str] = []
    denied_commands: list[str] = []
    handoff_required_outputs: list[str] = []
    completion_gates_required: list[str] = []
    allowed_workspaces: list[str] = []
    allowed_paths: list[str] = []
    readonly_paths: list[str] = []
    forbidden_paths: list[str] = []
    network_access: str = ""
    secret_allowlist: list[str] = []

    # v0.2: handoff contract reference (optional, replaces inline handoff)
    handoff_contract: str | None = None

    # v0.2: provenance metadata
    source_repository: str | None = None
    source_ref: str | None = None
    source_path: str | None = None
    source_hash: str | None = None

    @field_validator("id")
    @classmethod
    def id_not_empty(cls, v: str) -> str:
        if not v.strip():
            raise ValueError("role id must not be empty")
        return v.strip()

    @field_validator("permission_preset")
    @classmethod
    def preset_not_empty(cls, v: str) -> str:
        if not v.strip():
            raise ValueError("permission_preset must not be empty")
        return v.strip()


def role_from_dict(data: dict[str, Any]) -> RoleContract:
    """Convert a raw dict (from YAML) to a RoleContract."""
    handoff = data.get("handoff", {}) or {}
    completion = data.get("completion_gates", {}) or {}
    return RoleContract(
        id=data.get("id", ""),
        name=data.get("name", ""),
        description=data.get("description", ""),
        mission=data.get("mission", ""),
        non_goals=data.get("non_goals", ""),
        permission_preset=data.get("permission_preset", ""),
        allowed_tasks=data.get("allowed_tasks", []),
        forbidden_tasks=data.get("forbidden_tasks", []),
        allowed_commands=data.get("allowed_commands", []),
        denied_commands=data.get("denied_commands", []),
        handoff_required_outputs=handoff.get("required_outputs", []),
        completion_gates_required=completion.get("required", []),
        allowed_workspaces=data.get("allowed_workspaces", []),
        allowed_paths=data.get("allowed_paths", []),
        readonly_paths=data.get("readonly_paths", []),
        forbidden_paths=data.get("forbidden_paths", []),
        network_access=data.get("network_access", ""),
        secret_allowlist=data.get("secret_allowlist", []),
        # v0.2 fields
        handoff_contract=data.get("handoff_contract"),
        source_repository=data.get("source_repository"),
        source_ref=data.get("source_ref"),
        source_path=data.get("source_path"),
        source_hash=data.get("source_hash"),
    )


# ── Fleet Config ───────────────────────────────────────────────────────────────


class NetworkConfig(BaseModel):
    """Contract for network policy configuration in fleet.yaml.

    Defines the network isolation mode per agent and
    temporary access request infrastructure.
    """

    mode: str = "isolated"  # isolated | control-plane | proxy | extern
    default: str = "isolated"
    per_agent: dict[str, str] = {}

    @field_validator("mode")
    @classmethod
    def mode_valid(cls, v: str) -> str:
        allowed = {"isolated", "control-plane", "proxy", "extern"}
        if v not in allowed:
            raise ValueError(f"Invalid network mode: {v}. Must be one of: {', '.join(sorted(allowed))}")
        return v


class TokenBudget(BaseModel):
    """Token budget per session for each agent."""

    default: int = 50
    per_agent: dict[str, int] = {}


class AgentState(str, enum.Enum):
    """Lifecycle state of an agent in the fleet."""

    CREATED = "created"
    ACTIVE = "active"
    IDLE = "idle"
    COMPLETED = "completed"
    ARCHIVED = "archived"



class FleetConfigContract(BaseModel):
    """Contract for fleet.yaml project configuration."""

    fleet_version: str
    name: str
    team: str
    output_dir: str = ".fleet/generated"
    resources: dict[str, dict[str, str]] = {}
    network_policy: NetworkConfig = NetworkConfig()
    token_budget: TokenBudget = TokenBudget()
    agent_states: dict[str, AgentState] = {}

    @field_validator("fleet_version")
    @classmethod
    def version_not_empty(cls, v: str) -> str:
        if not v.strip():
            raise ValueError("fleet_version must not be empty")
        return v.strip()


def fleet_config_from_dict(data: dict[str, Any]) -> FleetConfigContract:
    """Convert a raw dict (from fleet.yaml) to a FleetConfigContract."""
    return FleetConfigContract(
        fleet_version=data.get("fleet_version", ""),
        name=data.get("name", ""),
        team=data.get("team", ""),
        output_dir=data.get("output_dir", ".fleet/generated"),
        resources=data.get("resources", {}),
    )


# ── Handoff Contract ───────────────────────────────────────────────────────────


class HandoffValidationRule(BaseModel):
    """A single validation rule within a HandoffContract."""

    field: str
    required: bool = False
    min_length: int | None = None
    max_length: int | None = None
    enum: list[str] | None = None
    min_items: int | None = None
    regex: str | None = None


class HandoffContract(BaseModel):
    """Contract for handoff YAML files (v0.2+).

    Defines the formal contract between roles when work is handed off.
    """

    id: str
    name: str = ""
    description: str = ""
    from_roles: list[str] = []
    allowed_next_roles: list[str] = []
    required_fields: list[str] = []
    validation_rules: list[HandoffValidationRule] = []
    completion_gate_required: list[str] = []

    @field_validator("id")
    @classmethod
    def id_not_empty(cls, v: str) -> str:
        if not v.strip():
            raise ValueError("handoff contract id must not be empty")
        return v.strip()


def handoff_from_dict(data: dict[str, Any]) -> HandoffContract:
    """Convert a raw dict (from YAML) to a HandoffContract."""
    rules_raw = data.get("validation_rules", []) or []
    rules = [HandoffValidationRule(**r) if isinstance(r, dict) else r for r in rules_raw]
    cg = data.get("completion_gate", {}) or {}
    return HandoffContract(
        id=data.get("id", ""),
        name=data.get("name", ""),
        description=data.get("description", ""),
        from_roles=data.get("from_roles", []),
        allowed_next_roles=data.get("allowed_next_roles", []),
        required_fields=data.get("required_fields", []),
        validation_rules=rules,
        completion_gate_required=cg.get("required", []),
    )


class HandoffValidationError(Exception):
    """Raised when a handoff document fails runtime validation."""


def validate_handoff_doc(
    doc: dict[str, Any],
    contract: HandoffContract,
    from_agent: str,
    to_agent: str,
) -> dict[str, Any]:
    """Validate a handoff document against its contract at runtime.

    Args:
        doc: The handoff document dict (from YAML/JSON).
        contract: The HandoffContract to validate against.
        from_agent: The sending agent ID.
        to_agent: The receiving agent ID.

    Returns:
        Dict with keys: passed (bool), checks (list of dicts).
        Each check: {"check": str, "status": "passed"|"failed", "message": str}.
    """
    checks: list[dict[str, str]] = []

    # 1. from_roles check
    if contract.from_roles:
        if from_agent in contract.from_roles:
            checks.append({"check": f"from_roles:{from_agent}", "status": "passed"})
        else:
            checks.append({
                "check": f"from_roles:{from_agent}",
                "status": "failed",
                "message": f"Agent '{from_agent}' not in contract's from_roles: {contract.from_roles}",
            })

    # 2. allowed_next_roles check
    if contract.allowed_next_roles:
        if to_agent in contract.allowed_next_roles:
            checks.append({"check": f"allowed_next_roles:{to_agent}", "status": "passed"})
        else:
            checks.append({
                "check": f"allowed_next_roles:{to_agent}",
                "status": "failed",
                "message": f"Agent '{to_agent}' not in contract's allowed_next_roles: {contract.allowed_next_roles}",
            })

    # 3. required_fields check
    for field in contract.required_fields:
        if field in doc and doc[field] is not None and doc[field] != "":
            checks.append({"check": f"required_field:{field}", "status": "passed"})
        else:
            checks.append({
                "check": f"required_field:{field}",
                "status": "failed",
                "message": f"Required field '{field}' missing or empty in handoff document",
            })

    # 4. validation_rules check
    for rule in contract.validation_rules:
        val = doc.get(rule.field)
        check_name = f"rule:{rule.field}"
        issues = []

        if rule.required and (val is None or val == ""):
            issues.append(f"field '{rule.field}' is required")
        if rule.min_length is not None and isinstance(val, str) and len(val) < rule.min_length:
            issues.append(f"min length {rule.min_length}")
        if rule.max_length is not None and isinstance(val, str) and len(val) > rule.max_length:
            issues.append(f"max length {rule.max_length}")
        if rule.enum is not None and val not in rule.enum:
            issues.append(f"must be one of: {rule.enum}")
        if rule.min_items is not None and isinstance(val, (list, dict)) and len(val) < rule.min_items:
            issues.append(f"min items {rule.min_items}")
        if rule.regex and isinstance(val, str):
            import re
            if not re.match(rule.regex, val):
                issues.append(f"regex mismatch: {rule.regex}")

        if issues:
            checks.append({"check": check_name, "status": "failed", "message": "; ".join(issues)})
        else:
            checks.append({"check": check_name, "status": "passed"})

    passed_all = all(c["status"] == "passed" for c in checks)
    return {"passed": passed_all, "checks": checks}


# ── Cross-Reference Validation ─────────────────────────────────────────────────


class FoundationLockSource(BaseModel):
    """A single foundation source entry in foundation.lock.yaml."""

    id: str
    version: str
    locked_at: str  # ISO date


class FoundationLock(BaseModel):
    """Contract for foundation.lock.yaml."""

    foundation_version: int = 1
    sources: list[FoundationLockSource]


class AgencyLock(BaseModel):
    """Contract for agency.lock.yaml."""

    agency_version: int = 1
    ref: str = "main"
    locked_at: str  # ISO date


class CheckResult:
    """Result of a single cross-reference check."""

    def __init__(self, status: str, check: str, message: str = ""):
        self.status = status
        self.check = check
        self.message = message


def validate_contract_cross_references(
    teams: dict[str, TeamContract] | list[TeamContract],
    roles: dict[str, RoleContract] | list[RoleContract],
    known_presets: list[str] | None = None,
    handoff_contracts: dict[str, HandoffContract] | None = None,
) -> list[CheckResult]:
    """Validate all cross-references between contracts.

    Accepts both dict and list forms for backward compatibility.
    Returns a list of CheckResult objects.
    """
    results: list[CheckResult] = []

    # Normalize to dict form
    if isinstance(teams, list):
        teams_dict = {t.id: t for t in teams}
    else:
        teams_dict = teams
    if isinstance(roles, list):
        roles_dict = {r.id: r for r in roles}
    else:
        roles_dict = roles

    # Resolve known presets: support both dict and list
    preset_ids: set[str]
    if known_presets is not None:
        preset_ids = set(known_presets)
    else:
        preset_ids = set()

    # Team → Role references
    for team_id, team in teams_dict.items():
        all_agents = team.agents + team.optional_agents
        for agent_id in all_agents:
            check_name = f"team:{team_id}.agent:{agent_id}"
            if agent_id in roles_dict:
                results.append(CheckResult("passed", check_name))
            else:
                results.append(
                    CheckResult(
                        "failed",
                        check_name,
                        f"Team '{team_id}' references agent '{agent_id}' "
                        f"but no role contract with that id exists",
                    )
                )

    # Role → Permission Preset references
    for role_id, role in roles_dict.items():
        check_name = f"role:{role_id}.preset:{role.permission_preset}"
        if role.permission_preset in preset_ids:
            results.append(CheckResult("passed", check_name))
        else:
            results.append(
                CheckResult(
                    "failed",
                    check_name,
                    f"Role '{role_id}' references permission preset "
                    f"'{role.permission_preset}' but no such preset exists",
                )
            )

    # Role → Handoff Contract references (v0.2+)
    if handoff_contracts is not None:
        for role_id, role in roles_dict.items():
            if role.handoff_contract:
                check_name = f"role:{role_id}.handoff:{role.handoff_contract}"
                if role.handoff_contract in handoff_contracts:
                    results.append(CheckResult("passed", check_name))
                else:
                    results.append(
                        CheckResult(
                            "failed",
                            check_name,
                            f"Role '{role_id}' references handoff contract "
                            f"'{role.handoff_contract}' but no such contract exists",
                        )
                    )

    # Handoff Contract → Role references
    if handoff_contracts is not None:
        all_role_ids = set(roles_dict.keys())
        for hc_id, hc in handoff_contracts.items():
            # v0.3: every handoff contract must define at least one required_field
            check_name = f"handoff:{hc_id}.required_fields"
            if not hc.required_fields:
                results.append(
                    CheckResult(
                        "failed",
                        check_name,
                        f"Handoff contract '{hc_id}' has no required_fields — "
                        f"at least one field is required for runtime validation",
                    )
                )
            else:
                results.append(CheckResult("passed", check_name))
            for r in hc.from_roles:
                check_name = f"handoff:{hc_id}.from_role:{r}"
                if r in all_role_ids:
                    results.append(CheckResult("passed", check_name))
                else:
                    results.append(
                        CheckResult(
                            "failed",
                            check_name,
                            f"Handoff contract '{hc_id}' references from_role "
                            f"'{r}' but no role with that id exists",
                        )
                    )
            for r in hc.allowed_next_roles:
                check_name = f"handoff:{hc_id}.to_role:{r}"
                if r in all_role_ids:
                    results.append(CheckResult("passed", check_name))
                else:
                    results.append(
                        CheckResult(
                            "failed",
                            check_name,
                            f"Handoff contract '{hc_id}' references "
                            f"allowed_next_role '{r}' but no role exists",
                        )
                    )

    # No duplicate IDs across teams and roles
    all_ids = set(teams_dict.keys()) & set(roles_dict.keys())
    for dup_id in all_ids:
        results.append(
            CheckResult(
                "failed",
                f"duplicate_id:{dup_id}",
                f"ID '{dup_id}' is used by both a team and a role",
            )
        )

    # No duplicate IDs across handoffs and teams/roles
    if handoff_contracts is not None:
        for hc_id in handoff_contracts:
            if hc_id in teams_dict or hc_id in roles_dict:
                results.append(
                    CheckResult(
                        "failed",
                        f"duplicate_id:{hc_id}",
                        f"ID '{hc_id}' is used by a handoff contract and "
                        f"also a team/role",
                    )
                )

    return results
