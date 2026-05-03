"""
Contract schemas and cross-reference validation for Hermes Fleet v0.2+.

Defines formal, validated data models for Team, Role, and Handoff
contracts. These are the machine-readable equivalent of the three design
pillars (Role, Boundary, Completion) — expressed as Pydantic models with
cross-reference validation.

v0.2 focus:
- TeamContract: which agents form a team
- RoleContract: what an agent is and what it can do
- HandoffContract: what a handoff must contain (Completion pillar)

Cross-reference validation ensures:
- Every team agent has a corresponding role definition
- Every role references a known permission preset
- Every handoff contract pairs known roles
"""

from typing import Any, Dict, List, Optional

from pydantic import BaseModel, Field, ValidationError, model_validator


class ContractValidationError(Exception):
    """Raised when a YAML definition fails schema validation."""


# ──────────────────────────────────────────────
# Fleet Config Contract
# ──────────────────────────────────────────────


class FleetConfigContract(BaseModel):
    """User-facing fleet.yaml configuration contract.

    Validates the minimal project configuration that users write
    by hand. Catches typos like ``teem`` instead of ``team`` early.
    """

    fleet_version: str = Field(default="0.1.0")
    name: str = Field(default="unnamed-fleet")
    team: str = Field(default="general-dev")
    output_dir: str = Field(default=".fleet/generated")


def fleet_config_from_dict(data: dict) -> FleetConfigContract:
    """Validate a raw fleet.yaml dict against FleetConfigContract.

    Raises:
        ContractValidationError: If the data fails validation.
    """
    try:
        return FleetConfigContract.model_validate(data)
    except ValidationError as e:
        raise ContractValidationError(
            f"fleet.yaml validation failed: {e}"
        ) from e


# ──────────────────────────────────────────────
# Permission Preset Contract
# ──────────────────────────────────────────────


class PermissionPresetContract(BaseModel):
    """A permission preset that defines filesystem, network, and secret access."""

    id: str
    allowed_workspaces: str
    filesystem: Dict[str, List[str]] = Field(default_factory=lambda: {
        "writable_paths": [],
        "readonly_paths": ["**"],
        "forbidden_paths": [],
    })
    network_access: str
    secret_allowlist: List[str] = Field(default_factory=list)


def permission_preset_from_dict(data: dict) -> PermissionPresetContract:
    """Validate a raw permission preset YAML dict against PermissionPresetContract.

    Raises:
        ContractValidationError: If the data fails validation.
    """
    try:
        return PermissionPresetContract.model_validate(data)
    except ValidationError as e:
        preset_id = data.get("id", "unknown")
        raise ContractValidationError(
            f"Permission preset '{preset_id}' validation failed: {e}"
        ) from e


# ──────────────────────────────────────────────
# Team Contract
# ──────────────────────────────────────────────


class TeamContract(BaseModel):
    """A formal team composition contract.

    Maps a team ID to its agent roster. Each agent ID must resolve
    to a RoleContract in the role inventory.
    """

    id: str
    name: str
    description: str
    agents: List[str] = Field(min_length=1)
    optional_agents: Dict[str, bool] = Field(default_factory=dict)

    @model_validator(mode="after")
    def _no_duplicate_agents(self) -> "TeamContract":
        seen = set()
        for a in self.agents:
            if a in seen:
                raise ValueError(f"Duplicate agent '{a}' in team '{self.id}'")
            seen.add(a)
        return self


# ──────────────────────────────────────────────
# Role Contract
# ──────────────────────────────────────────────


class RoleContract(BaseModel):
    """A formal role definition contract.

    Captures identity (Role pillar), task scope, and boundary
    constraints. The permission_preset must resolve to a known
    preset in the permission presets inventory.
    """

    id: str
    name: str
    description: str
    mission: str
    non_goals: str
    permission_preset: str
    allowed_tasks: List[str] = Field(min_length=1)
    forbidden_tasks: List[str] = Field(default_factory=list)
    allowed_commands: List[str] = Field(default_factory=list)
    denied_commands: List[str] = Field(default_factory=list)
    handoff: Dict[str, Any] = Field(default_factory=dict)
    completion_gates: Dict[str, Any] = Field(default_factory=dict)

    @model_validator(mode="after")
    def _handoff_has_required_outputs(self) -> "RoleContract":
        """Handoff must specify at least one required output."""
        outputs = self.handoff.get("required_outputs", [])
        if not outputs:
            raise ValueError(
                f"Role '{self.id}' handoff has no required_outputs"
            )
        return self

    @model_validator(mode="after")
    def _completion_has_required_gates(self) -> "RoleContract":
        """Completion gates must specify at least one required gate."""
        required = self.completion_gates.get("required", [])
        if not required:
            raise ValueError(
                f"Role '{self.id}' completion_gates has no required gates"
            )
        return self


# ──────────────────────────────────────────────
# Handoff Contract
# ──────────────────────────────────────────────


class HandoffContract(BaseModel):
    """A formal handoff contract between roles.

    Defines what must be communicated when one role hands off
    to another (Completion pillar). from_roles and allowed_next_roles
    must resolve to known RoleContracts.
    """

    id: str
    from_roles: List[str] = Field(min_length=1)
    allowed_next_roles: List[str] = Field(min_length=1)
    required_fields: List[str] = Field(min_length=1)
    validation_rules: List[Dict[str, Any]] = Field(default_factory=list)

    @model_validator(mode="after")
    def _no_self_handoff(self) -> "HandoffContract":
        """A role should not hand off to itself."""
        for fr in self.from_roles:
            if fr in self.allowed_next_roles:
                raise ValueError(
                    f"Handoff '{self.id}': role '{fr}' is both sender and receiver"
                )
        return self


# ──────────────────────────────────────────────
# YAML → Contract Helpers
# ──────────────────────────────────────────────


def team_from_dict(data: dict) -> TeamContract:
    """Validate a raw YAML dict against TeamContract schema.

    Raises:
        ContractValidationError: If the data fails validation.
    """
    try:
        return TeamContract.model_validate(data)
    except ValidationError as e:
        raise ContractValidationError(
            f"Team contract validation failed for '{data.get('id', 'unknown')}': {e}"
        ) from e


def role_from_dict(data: dict) -> RoleContract:
    """Validate a raw YAML dict against RoleContract schema.

    Raises:
        ContractValidationError: If the data fails validation.
    """
    try:
        return RoleContract.model_validate(data)
    except ValidationError as e:
        raise ContractValidationError(
            f"Role contract validation failed for '{data.get('id', 'unknown')}': {e}"
        ) from e


# ──────────────────────────────────────────────
# Cross-Reference Validation
# ──────────────────────────────────────────────


class CrossReferenceResult(BaseModel):
    """Result of a single cross-reference validation check."""

    check: str
    status: str  # "passed" | "failed"
    message: str = ""


def validate_contract_cross_references(
    teams: List[TeamContract],
    roles: List[RoleContract],
    handoffs: Optional[List[HandoffContract]] = None,
    known_presets: Optional[List[str]] = None,
) -> List[CrossReferenceResult]:
    """Validate that all cross-references between contracts resolve.

    Checks:
    1. All team agents have corresponding role contracts
    2. All role permission_presets resolve to known presets
    3. All handoff from/allowed_next roles have corresponding role contracts
    4. No duplicate contract IDs within each type
    """
    results: List[CrossReferenceResult] = []

    role_ids = {r.id for r in roles}
    team_ids = {t.id for t in teams}
    preset_ids = set(known_presets or [])
    handoff_ids: set[str] = set()

    # ── 1. Team → Role references ──
    for team in teams:
        for agent_id in team.agents:
            if agent_id not in role_ids:
                results.append(CrossReferenceResult(
                    check=f"team.{team.id}.agent.{agent_id}",
                    status="failed",
                    message=f"Team '{team.id}' references unknown role '{agent_id}'",
                ))

    if not any(r.status == "failed" for r in results if "team." in r.check):
        results.append(CrossReferenceResult(
            check="team_role_references",
            status="passed",
            message="All team agents have corresponding role contracts",
        ))

    # ── 2. Role → Permission preset references ──
    if preset_ids:
        for role in roles:
            if role.permission_preset not in preset_ids:
                results.append(CrossReferenceResult(
                    check=f"role.{role.id}.permission_preset",
                    status="failed",
                    message=(
                        f"Role '{role.id}' references unknown permission "
                        f"preset '{role.permission_preset}'"
                    ),
                ))

        if not any(r.status == "failed" for r in results if "permission_preset" in r.check):
            results.append(CrossReferenceResult(
                check="role_preset_references",
                status="passed",
                message="All role permission_presets resolve to known presets",
            ))

    # ── 3. Handoff → Role references ──
    if handoffs:
        for hc in handoffs:
            for role_id in hc.from_roles + hc.allowed_next_roles:
                if role_id not in role_ids:
                    results.append(CrossReferenceResult(
                        check=f"handoff.{hc.id}.role.{role_id}",
                        status="failed",
                        message=(
                            f"Handoff '{hc.id}' references unknown "
                            f"role '{role_id}'"
                        ),
                    ))

        if not any(r.status == "failed" for r in results if "handoff." in r.check):
            results.append(CrossReferenceResult(
                check="handoff_role_references",
                status="passed",
                message="All handoff contracts reference known roles",
            ))

    # ── 4. No duplicate contract IDs ──
    seen_ids: dict[str, str] = {}
    # Check teams
    for t in teams:
        if t.id in seen_ids:
            results.append(CrossReferenceResult(
                check=f"duplicate_id.{t.id}",
                status="failed",
                message=f"Duplicate contract ID '{t.id}' (team conflicts with {seen_ids[t.id]})",
            ))
        seen_ids[t.id] = "team"

    # Check roles
    for r in roles:
        if r.id in seen_ids:
            results.append(CrossReferenceResult(
                check=f"duplicate_id.{r.id}",
                status="failed",
                message=f"Duplicate contract ID '{r.id}' (role conflicts with {seen_ids[r.id]})",
            ))
        seen_ids[r.id] = "role"

    # Check handoffs
    if handoffs:
        for hc in handoffs:
            if hc.id in seen_ids:
                results.append(CrossReferenceResult(
                    check=f"duplicate_id.{hc.id}",
                    status="failed",
                    message=f"Duplicate contract ID '{hc.id}' (handoff conflicts with {seen_ids[hc.id]})",
                ))
            seen_ids[hc.id] = "handoff"

    if not any(r.status == "failed" for r in results if "duplicate_id" in r.check):
        results.append(CrossReferenceResult(
            check="no_duplicate_ids",
            status="passed",
            message="No duplicate contract IDs across all contract types",
        ))

    # Add a single all-clear result if everything passed
    if not any(r.status == "failed" for r in results):
        results.append(CrossReferenceResult(
            check="all_cross_references",
            status="passed",
            message="All contract cross-references resolved successfully",
        ))

    return results
