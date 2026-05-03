"""
Tests: Preset loader — converting YAML presets to contract models.

Tests that the loader correctly transforms v0.1 preset YAML data
into v0.2+ Pydantic contract models. No file I/O in assertions,
no real AI, Docker, or Hermes agent execution.
"""

from hermes_fleet.loader import (
    load_team_contract,
    load_role_contract,
    load_all_team_contracts,
    load_all_role_contracts,
    load_known_presets,
    load_known_role_ids,
)
from hermes_fleet.schema import (
    TeamContract,
    RoleContract,
    RoleFidelityMode,
)


class TestLoadTeamContract:
    """Tests for load_team_contract()."""

    def test_general_dev_loads(self):
        tc = load_team_contract("general-dev")
        assert tc is not None
        assert isinstance(tc, TeamContract)
        assert tc.id == "general-dev"
        assert len(tc.role_inventory) >= 3
        assert "orchestrator" in tc.role_inventory

    def test_saas_medium_loads(self):
        tc = load_team_contract("saas-medium")
        assert tc is not None
        assert tc.id == "saas-medium"
        assert len(tc.role_inventory) == 9
        assert "security-reviewer" in tc.role_inventory

    def test_permission_preset_mapping_is_populated(self):
        tc = load_team_contract("saas-medium")
        assert tc is not None
        # Every role should have a mapped preset
        for role_id in tc.role_inventory:
            assert role_id in tc.permission_preset_mapping, (
                f"Role '{role_id}' missing permission preset mapping"
            )

    def test_security_reviewer_has_correct_preset(self):
        tc = load_team_contract("saas-medium")
        assert tc is not None
        assert tc.permission_preset_mapping.get("security-reviewer") in (
            "readonly_no_network", "repo_readonly"
        )

    def test_unknown_team_returns_none(self):
        tc = load_team_contract("nonexistent-team")
        assert tc is None


class TestLoadRoleContract:
    """Tests for load_role_contract()."""

    def test_orchestrator_loads(self):
        rc = load_role_contract("orchestrator")
        assert rc is not None
        assert isinstance(rc, RoleContract)
        assert rc.id == "orchestrator"
        assert rc.role_fidelity_mode == RoleFidelityMode.NEAR_VERBATIM

    def test_security_reviewer_loads(self):
        rc = load_role_contract("security-reviewer")
        assert rc is not None
        assert "security_review" in rc.allowed_task_types
        assert "implementation" in rc.forbidden_task_types

    def test_custom_fidelity_mode(self):
        rc = load_role_contract(
            "orchestrator",
            role_fidelity_mode=RoleFidelityMode.PRESERVE,
            source_ref="v1.0.0",
        )
        assert rc is not None
        assert rc.role_fidelity_mode == RoleFidelityMode.PRESERVE
        assert rc.source.ref == "v1.0.0"

    def test_unknown_role_returns_none(self):
        rc = load_role_contract("nonexistent-role")
        assert rc is None


class TestLoadAllContracts:
    """Tests for bulk loading functions."""

    def test_load_all_team_contracts(self):
        teams = load_all_team_contracts()
        assert len(teams) >= 2
        team_ids = [tc.id for tc in teams]
        assert "general-dev" in team_ids
        assert "saas-medium" in team_ids

    def test_load_all_role_contracts(self):
        roles = load_all_role_contracts()
        assert len(roles) >= 11
        role_ids = [rc.id for rc in roles]
        assert "orchestrator" in role_ids
        assert "security-reviewer" in role_ids
        assert "frontend-developer" in role_ids

    def test_all_team_contracts_have_permission_mappings(self):
        for tc in load_all_team_contracts():
            for role_id in tc.role_inventory:
                assert role_id in tc.permission_preset_mapping, (
                    f"Team '{tc.id}' role '{role_id}' missing preset mapping"
                )

    def test_known_presets(self):
        presets = load_known_presets()
        assert len(presets) >= 5
        assert "orchestrator_safe" in presets
        assert "readonly_no_network" in presets

    def test_known_role_ids(self):
        role_ids = load_known_role_ids()
        assert len(role_ids) >= 11
        assert "orchestrator" in role_ids


class TestLoaderContractValidationIntegration:
    """Tests that loader output can be fed into contract validation."""

    def test_all_teams_pass_contract_validation(self):
        from hermes_fleet.contracts import validate_team_contract

        known_presets = load_known_presets()
        known_role_ids = load_known_role_ids()

        for tc in load_all_team_contracts():
            results = validate_team_contract(
                tc,
                known_role_ids=known_role_ids,
                known_presets=known_presets,
                known_handoff_contracts=None,
            )
            failed = [r for r in results if r["status"] == "failed"]
            assert len(failed) == 0, (
                f"Team '{tc.id}' validation failures: {failed}"
            )

    def test_all_roles_pass_contract_validation(self):
        from hermes_fleet.contracts import validate_role_contract

        known_presets = load_known_presets()

        for rc in load_all_role_contracts():
            results = validate_role_contract(
                rc,
                known_presets=known_presets,
                known_handoff_contracts=None,
            )
            # Allow source_ref failures for v0.1 presets (no upstream ref)
            failed = [r for r in results if r["status"] == "failed"
                      and "source_ref" not in r["check"]]
            assert len(failed) == 0, (
                f"Role '{rc.id}' validation failures: {failed}"
            )
