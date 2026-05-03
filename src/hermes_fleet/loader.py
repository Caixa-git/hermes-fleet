"""
Preset loader — converts YAML preset dicts into Pydantic contract models.

This is the bridge between the v0.1 preset files (raw YAML dicts)
and the v0.2+ contract validation system (Pydantic models).

File I/O is delegated to teams.py; this module only transforms data.
"""

from typing import Dict, List, Optional

from hermes_fleet.policy import list_presets
from hermes_fleet.schema import (
    RoleFidelityMode,
    SourceProvenance,
    TeamContract,
    RoleContract,
)
from hermes_fleet.teams import load_role, load_team, list_available_roles, list_available_teams


def load_team_contract(team_id: str) -> Optional[TeamContract]:
    """
    Load a team preset as a TeamContract Pydantic model.

    Converts the v0.1 team preset YAML format into the v0.2+
    TeamContract schema. Permission presets are resolved from
    each role's YAML definition.
    """
    team_data = load_team(team_id)
    if not team_data:
        return None

    agents = team_data.get("agents", [])
    permission_mapping: Dict[str, str] = {}
    for agent_id in agents:
        role_data = load_role(agent_id) or {}
        preset_id = role_data.get("permission_preset", "repo_readonly")
        permission_mapping[agent_id] = preset_id

    return TeamContract(
        id=team_id,
        required_capabilities=[],
        role_inventory=agents,
        permission_preset_mapping=permission_mapping,
        handoff_contract_inventory=[],
    )


def load_role_contract(
    role_id: str,
    role_fidelity_mode: RoleFidelityMode = RoleFidelityMode.NEAR_VERBATIM,
    source_ref: str = "v0.1",
) -> Optional[RoleContract]:
    """
    Load a role preset as a RoleContract Pydantic model.

    Converts the v0.1 role preset YAML format into the v0.2+
    RoleContract schema. Default fidelity mode is NEAR_VERBATIM
    since v0.1 presets don't have source provenance tracking.
    """
    role_data = load_role(role_id)
    if not role_data:
        return None

    allowed = role_data.get("allowed_tasks", [])
    forbidden = role_data.get("forbidden_tasks", [])
    preset_id = role_data.get("permission_preset", "repo_readonly")
    handoff_contract_id = ""

    return RoleContract(
        id=role_id,
        source=SourceProvenance(ref=source_ref),
        role_fidelity_mode=role_fidelity_mode,
        allowed_task_types=allowed,
        forbidden_task_types=forbidden,
        permission_preset=preset_id,
        handoff_contract=handoff_contract_id,
    )


def load_all_team_contracts() -> List[TeamContract]:
    """Load all available team presets as TeamContract models."""
    return [
        tc for team_id in list_available_teams()
        if (tc := load_team_contract(team_id)) is not None
    ]


def load_all_role_contracts(
    fidelity_mode: RoleFidelityMode = RoleFidelityMode.NEAR_VERBATIM,
    source_ref: str = "v0.1",
) -> List[RoleContract]:
    """Load all available role presets as RoleContract models."""
    return [
        rc for role_id in list_available_roles()
        if (rc := load_role_contract(role_id, fidelity_mode, source_ref)) is not None
    ]


def load_known_presets() -> List[str]:
    """Load the list of known permission preset IDs."""
    return list_presets()


def load_known_role_ids() -> List[str]:
    """Load the list of known role IDs."""
    return list_available_roles()
