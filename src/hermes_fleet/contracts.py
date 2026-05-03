"""
Contract validation module (v0.2+).

Pure validation functions for Team Contracts, Role Contracts,
Handoff Contracts, and Team Proposals. Each function takes
Pydantic model instances (or dicts) and returns a list of
CheckResult dicts.

These functions are the building blocks for:
- Contract Schema Tests
- Cross-Reference Tests
- Safety Invariant Tests
- Deterministic Allocation Tests
- Handoff Validation Tests

File I/O is NOT handled here — callers load models first.
"""

from typing import Dict, List, Optional

from hermes_fleet.schema import (
    CompletionGate,
    HandoffContractSchema,
    RoleContract,
    RoleFidelityMode,
    TeamContract,
    TeamProposal,
    ValidationRule,
)


def check_result(check: str, status: str, message: str = "") -> dict:
    """Create a standard check result dict."""
    return {"check": check, "status": status, "message": message}


# ──────────────────────────────────────────────
# Team Contract Validation
# ──────────────────────────────────────────────


def validate_team_contract(
    tc: TeamContract,
    known_role_ids: Optional[List[str]] = None,
    known_presets: Optional[List[str]] = None,
    known_handoff_contracts: Optional[List[str]] = None,
) -> List[dict]:
    """
    Validate a Team Contract against known inventories.

    Returns a list of check results. All must be "passed" for the
    contract to be considered valid.
    """
    results = []

    # Required field: id
    if not tc.id:
        results.append(check_result(
            "team_contract_id_required", "failed",
            "TeamContract.id is required",
        ))
    else:
        results.append(check_result(
            "team_contract_id_required", "passed",
        ))

    # Required field: role_inventory must not be empty
    if not tc.role_inventory:
        results.append(check_result(
            "team_contract_role_inventory", "failed",
            f"TeamContract '{tc.id}' has empty role_inventory",
        ))
    else:
        results.append(check_result(
            "team_contract_role_inventory", "passed",
            f"{len(tc.role_inventory)} roles defined",
        ))

    # Every role in role_inventory must have a permission_preset_mapping
    missing_mappings = [
        rid for rid in tc.role_inventory
        if rid not in tc.permission_preset_mapping
    ]
    if missing_mappings:
        results.append(check_result(
            "team_contract_permission_mapping", "failed",
            f"Roles missing permission preset mapping: {missing_mappings}",
        ))
    else:
        results.append(check_result(
            "team_contract_permission_mapping", "passed",
        ))

    # Cross-reference: known_role_ids
    if known_role_ids is not None:
        unknown_roles = [r for r in tc.role_inventory if r not in known_role_ids]
        if unknown_roles:
            results.append(check_result(
                "team_contract_roles_exist", "failed",
                f"Unknown roles in inventory: {unknown_roles}",
            ))
        else:
            results.append(check_result(
                "team_contract_roles_exist", "passed",
            ))

    # Cross-reference: known_presets
    if known_presets is not None:
        unknown_presets = [
            p for p in tc.permission_preset_mapping.values()
            if p not in known_presets
        ]
        if unknown_presets:
            results.append(check_result(
                "team_contract_presets_exist", "failed",
                f"Unknown permission presets: {unknown_presets}",
            ))
        else:
            results.append(check_result(
                "team_contract_presets_exist", "passed",
            ))

    # Cross-reference: known_handoff_contracts
    if known_handoff_contracts is not None:
        unknown_handoffs = [
            h for h in tc.handoff_contract_inventory
            if h not in known_handoff_contracts
        ]
        if unknown_handoffs:
            results.append(check_result(
                "team_contract_handoffs_exist", "failed",
                f"Unknown handoff contracts: {unknown_handoffs}",
            ))
        else:
            results.append(check_result(
                "team_contract_handoffs_exist", "passed",
            ))

    return results


# ──────────────────────────────────────────────
# Role Contract Validation
# ──────────────────────────────────────────────


def validate_role_contract(
    rc: RoleContract,
    known_presets: Optional[List[str]] = None,
    known_handoff_contracts: Optional[List[str]] = None,
) -> List[dict]:
    """
    Validate a Role Contract against known inventories and invariants.
    """
    results = []

    # Required field: id
    if not rc.id:
        results.append(check_result(
            "role_contract_id_required", "failed",
            "RoleContract.id is required",
        ))
    else:
        results.append(check_result(
            "role_contract_id_required", "passed",
        ))

    # Role Fidelity Mode must be a valid enum value
    if rc.role_fidelity_mode not in RoleFidelityMode:
        results.append(check_result(
            "role_contract_fidelity_mode", "failed",
            f"Invalid role_fidelity_mode: {rc.role_fidelity_mode}",
        ))
    else:
        results.append(check_result(
            "role_contract_fidelity_mode", "passed",
            f"mode={rc.role_fidelity_mode.value}",
        ))

    # Allowed and forbidden task types must not overlap
    if rc.allowed_task_types and rc.forbidden_task_types:
        overlap = set(rc.allowed_task_types) & set(rc.forbidden_task_types)
        if overlap:
            results.append(check_result(
                "role_contract_task_types_no_overlap", "failed",
                f"Task types in both allowed and forbidden: {overlap}",
            ))
        else:
            results.append(check_result(
                "role_contract_task_types_no_overlap", "passed",
            ))
    else:
        results.append(check_result(
            "role_contract_task_types_no_overlap", "passed",
            "No task types defined (no overlap possible)",
        ))

    # Permission preset must be known
    if known_presets is not None:
        if rc.permission_preset not in known_presets:
            results.append(check_result(
                "role_contract_preset_exists", "failed",
                f"Unknown permission preset: {rc.permission_preset}",
            ))
        else:
            results.append(check_result(
                "role_contract_preset_exists", "passed",
            ))

    # Handoff contract reference must be known
    if known_handoff_contracts is not None and rc.handoff_contract:
        if rc.handoff_contract not in known_handoff_contracts:
            results.append(check_result(
                "role_contract_handoff_exists", "failed",
                f"Unknown handoff contract: {rc.handoff_contract}",
            ))
        else:
            results.append(check_result(
                "role_contract_handoff_exists", "passed",
            ))

    # Source ref should be set for preserve mode
    if rc.role_fidelity_mode == RoleFidelityMode.PRESERVE:
        if not rc.source.ref:
            results.append(check_result(
                "role_contract_source_ref_for_preserve", "failed",
                "Preserve mode requires source.ref to be set",
            ))
        else:
            results.append(check_result(
                "role_contract_source_ref_for_preserve", "passed",
                f"ref={rc.source.ref}",
            ))

    return results


# ──────────────────────────────────────────────
# Handoff Contract Validation
# ──────────────────────────────────────────────


def validate_handoff_contract(
    hc: HandoffContractSchema,
    known_role_ids: Optional[List[str]] = None,
) -> List[dict]:
    """
    Validate a Handoff Contract against invariants.
    """
    results = []

    # Required field: id
    if not hc.id:
        results.append(check_result(
            "handoff_contract_id_required", "failed",
            "HandoffContractSchema.id is required",
        ))
    else:
        results.append(check_result(
            "handoff_contract_id_required", "passed",
        ))

    # Required fields should be a subset of validation_rules fields
    rule_fields = {vr.field for vr in hc.validation_rules}
    missing_rules = [f for f in hc.required_fields if f not in rule_fields]
    if missing_rules:
        results.append(check_result(
            "handoff_contract_required_fields_have_rules", "failed",
            f"Required fields missing validation rules: {missing_rules}",
        ))
    else:
        results.append(check_result(
            "handoff_contract_required_fields_have_rules", "passed",
        ))

    # from_roles and allowed_next_roles must not overlap
    if hc.from_roles and hc.allowed_next_roles:
        overlap = set(hc.from_roles) & set(hc.allowed_next_roles)
        if overlap:
            results.append(check_result(
                "handoff_contract_no_self_handoff", "failed",
                f"from_roles and allowed_next_roles overlap: {overlap}",
            ))
        else:
            results.append(check_result(
                "handoff_contract_no_self_handoff", "passed",
            ))
    else:
        results.append(check_result(
            "handoff_contract_no_self_handoff", "passed",
            "No overlap check (one or both lists empty)",
        ))

    # Cross-reference: known_role_ids
    if known_role_ids is not None:
        all_role_refs = set(hc.from_roles) | set(hc.allowed_next_roles)
        unknown_roles = [r for r in all_role_refs if r not in known_role_ids]
        if unknown_roles:
            results.append(check_result(
                "handoff_contract_roles_exist", "failed",
                f"Unknown role references: {unknown_roles}",
            ))
        else:
            results.append(check_result(
                "handoff_contract_roles_exist", "passed",
            ))

    return results


# ──────────────────────────────────────────────
# Team Proposal Validation
# ──────────────────────────────────────────────


def validate_team_proposal(
    tp: TeamProposal,
    known_team_ids: Optional[List[str]] = None,
    known_role_ids: Optional[List[str]] = None,
    known_presets: Optional[List[str]] = None,
    known_handoff_contracts: Optional[List[str]] = None,
) -> List[dict]:
    """
    Validate a Team Proposal against known inventories.
    """
    results = []

    # Required fields
    if not tp.goal:
        results.append(check_result(
            "team_proposal_goal_required", "failed",
            "TeamProposal.goal is required",
        ))
    else:
        results.append(check_result(
            "team_proposal_goal_required", "passed",
        ))

    if not tp.recommended_team_id:
        results.append(check_result(
            "team_proposal_team_id_required", "failed",
            "TeamProposal.recommended_team_id is required",
        ))
    else:
        results.append(check_result(
            "team_proposal_team_id_required", "passed",
        ))

    # Cross-reference: team ID must exist
    if known_team_ids is not None and tp.recommended_team_id:
        if tp.recommended_team_id not in known_team_ids:
            results.append(check_result(
                "team_proposal_team_exists", "failed",
                f"Unknown team: {tp.recommended_team_id}",
            ))
        else:
            results.append(check_result(
                "team_proposal_team_exists", "passed",
            ))

    # Customization roles must exist
    if known_role_ids is not None and tp.customizations.agents:
        unknown_roles = [
            r for r in tp.customizations.agents
            if r not in known_role_ids
        ]
        if unknown_roles:
            results.append(check_result(
                "team_proposal_custom_roles_exist", "failed",
                f"Unknown roles in customizations: {unknown_roles}",
            ))
        else:
            results.append(check_result(
                "team_proposal_custom_roles_exist", "passed",
            ))

    # Permission overrides must reference known presets
    if known_presets is not None and tp.customizations.permission_overrides:
        unknown_presets = [
            p for p in tp.customizations.permission_overrides.values()
            if p not in known_presets
        ]
        if unknown_presets:
            results.append(check_result(
                "team_proposal_permission_overrides_exist", "failed",
                f"Unknown presets in overrides: {unknown_presets}",
            ))
        else:
            results.append(check_result(
                "team_proposal_permission_overrides_exist", "passed",
            ))

    # Handoff overrides must reference known contracts
    if known_handoff_contracts is not None and tp.customizations.handoff_overrides:
        unknown_handoffs = [
            h for h in tp.customizations.handoff_overrides.values()
            if h not in known_handoff_contracts
        ]
        if unknown_handoffs:
            results.append(check_result(
                "team_proposal_handoff_overrides_exist", "failed",
                f"Unknown handoff contracts in overrides: {unknown_handoffs}",
            ))
        else:
            results.append(check_result(
                "team_proposal_handoff_overrides_exist", "passed",
            ))

    return results


# ──────────────────────────────────────────────
# Comprehensive Cross-Reference Validation
# ──────────────────────────────────────────────


def validate_all_cross_references(
    team_contracts: List[TeamContract],
    role_contracts: List[RoleContract],
    handoff_contracts: List[HandoffContractSchema],
    known_presets: List[str],
) -> List[dict]:
    """
    Run all cross-reference validations across all contracts.
    """
    results = []

    known_role_ids = [rc.id for rc in role_contracts]
    known_handoff_ids = [hc.id for hc in handoff_contracts]
    known_team_ids = [tc.id for tc in team_contracts]

    # Validate each Team Contract
    for tc in team_contracts:
        results.extend(validate_team_contract(
            tc,
            known_role_ids=known_role_ids,
            known_presets=known_presets,
            known_handoff_contracts=known_handoff_ids,
        ))

    # Validate each Role Contract
    for rc in role_contracts:
        results.extend(validate_role_contract(
            rc,
            known_presets=known_presets,
            known_handoff_contracts=known_handoff_ids,
        ))

    # Validate each Handoff Contract
    for hc in handoff_contracts:
        results.extend(validate_handoff_contract(
            hc,
            known_role_ids=known_role_ids,
        ))

    # Check all handoff contracts are referenced by at least one role
    all_role_handoff_refs = {
        rc.handoff_contract for rc in role_contracts if rc.handoff_contract
    }
    for hc in handoff_contracts:
        if hc.id not in all_role_handoff_refs:
            results.append(check_result(
                "handoff_contract_referenced_by_role", "failed",
                f"HandoffContract '{hc.id}' is not referenced by any RoleContract",
            ))
        else:
            results.append(check_result(
                "handoff_contract_referenced_by_role", "passed",
                f"HandoffContract '{hc.id}' is referenced",
            ))

    return results
