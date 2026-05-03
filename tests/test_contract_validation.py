"""
Tests: Contract validation functions.

Tests the pure validation functions in hermes_fleet.contracts.
No file I/O, no real AI, no Docker, no Hermes agent execution.
"""

import pytest

from hermes_fleet.contracts import (
    validate_team_contract,
    validate_role_contract,
    validate_handoff_contract,
    validate_team_proposal,
    validate_all_cross_references,
)
from hermes_fleet.schema import (
    TeamContract,
    RoleContract,
    RoleFidelityMode,
    HandoffContractSchema,
    TeamProposal,
    SourceProvenance,
    ValidationRule,
    CompletionGate,
)


# ──────────────────────────────────────────────
# Fixtures
# ──────────────────────────────────────────────


@pytest.fixture
def valid_team_contract():
    return TeamContract(
        id="saas-medium",
        required_capabilities=["frontend", "backend", "security"],
        role_inventory=["frontend-developer", "backend-developer", "security-reviewer"],
        permission_preset_mapping={
            "frontend-developer": "frontend_worktree_rw",
            "backend-developer": "backend_worktree_rw",
            "security-reviewer": "readonly_no_network",
        },
        handoff_contract_inventory=[
            "frontend_to_reviewer",
            "backend_to_security",
        ],
    )


@pytest.fixture
def valid_role_contract():
    return RoleContract(
        id="security-reviewer",
        source=SourceProvenance(
            repository="https://github.com/agency-agents/agency-agents",
            ref="v1.2.0",
            path="roles/security-reviewer.yaml",
            hash="sha256:abc123",
        ),
        role_fidelity_mode=RoleFidelityMode.PRESERVE,
        allowed_task_types=["security_review", "risk_analysis"],
        forbidden_task_types=["implementation", "deployment"],
        permission_preset="readonly_no_network",
        handoff_contract="security-reviewer_handoff",
    )


@pytest.fixture
def valid_handoff_contract():
    return HandoffContractSchema(
        id="security-reviewer_handoff",
        from_roles=["backend-developer", "fullstack-developer"],
        allowed_next_roles=["orchestrator", "technical-writer"],
        required_fields=["risk_summary", "approval_or_block"],
        validation_rules=[
            ValidationRule(field="risk_summary", required=True, min_length=50),
            ValidationRule(
                field="approval_or_block",
                required=True,
                enum=["approve", "block", "needs_discussion"],
            ),
        ],
        completion_gate=CompletionGate(
            required=["explicit_approve_or_block", "no_code_modification"]
        ),
    )


@pytest.fixture
def valid_proposal():
    return TeamProposal(
        goal="Build a SaaS MVP",
        recommended_team_id="saas-medium",
        rationale="SaaS team covers all required capabilities",
    )


@pytest.fixture
def known_inventories():
    return {
        "role_ids": [
            "orchestrator", "frontend-developer", "backend-developer",
            "security-reviewer", "reviewer", "qa-tester",
            "fullstack-developer", "technical-writer",
        ],
        "presets": [
            "orchestrator_safe", "repo_readonly", "readonly_no_network",
            "frontend_worktree_rw", "backend_worktree_rw", "docs_rw_repo_ro",
        ],
        "handoff_ids": [
            "security-reviewer_handoff", "frontend_to_reviewer",
            "backend_to_security",
        ],
        "team_ids": ["general-dev", "saas-medium"],
    }


# ──────────────────────────────────────────────
# Team Contract Tests
# ──────────────────────────────────────────────


class TestValidateTeamContract:
    """validate_team_contract tests."""

    def test_valid_contract_passes(self, valid_team_contract, known_inventories):
        results = validate_team_contract(
            valid_team_contract,
            known_role_ids=known_inventories["role_ids"],
            known_presets=known_inventories["presets"],
            known_handoff_contracts=known_inventories["handoff_ids"],
        )
        failed = [r for r in results if r["status"] == "failed"]
        assert len(failed) == 0, f"Expected 0 failures, got: {failed}"

    def test_empty_id_fails(self):
        tc = TeamContract(id="")
        results = validate_team_contract(tc)
        assert any(r["status"] == "failed" and "id" in r["check"] for r in results)

    def test_empty_role_inventory_fails(self):
        tc = TeamContract(id="test", role_inventory=[])
        results = validate_team_contract(tc)
        assert any(r["status"] == "failed" and "role_inventory" in r["check"] for r in results)

    def test_unknown_role_fails(self, valid_team_contract):
        results = validate_team_contract(
            valid_team_contract, known_role_ids=["orchestrator"]
        )
        assert any(r["status"] == "failed" and "roles_exist" in r["check"] for r in results)

    def test_unknown_preset_fails(self, valid_team_contract, known_inventories):
        results = validate_team_contract(
            valid_team_contract,
            known_role_ids=known_inventories["role_ids"],
            known_presets=["repo_readonly"],  # missing frontend_worktree_rw etc.
        )
        assert any(r["status"] == "failed" and "presets_exist" in r["check"] for r in results)

    def test_missing_permission_mapping_fails(self):
        tc = TeamContract(
            id="test",
            role_inventory=["role-a", "role-b"],
            permission_preset_mapping={"role-a": "preset_x"},  # role-b missing
        )
        results = validate_team_contract(tc)
        assert any(r["status"] == "failed" and "permission_mapping" in r["check"] for r in results)


class TestValidateRoleContract:
    """validate_role_contract tests."""

    def test_valid_contract_passes(self, valid_role_contract, known_inventories):
        results = validate_role_contract(
            valid_role_contract,
            known_presets=known_inventories["presets"],
            known_handoff_contracts=known_inventories["handoff_ids"],
        )
        failed = [r for r in results if r["status"] == "failed"]
        assert len(failed) == 0, f"Expected 0 failures, got: {failed}"

    def test_empty_id_fails(self):
        rc = RoleContract(id="")
        results = validate_role_contract(rc)
        assert any(r["status"] == "failed" and "id" in r["check"] for r in results)

    def test_overlapping_task_types_fails(self):
        rc = RoleContract(
            id="test",
            allowed_task_types=["security_review", "implementation"],
            forbidden_task_types=["implementation", "deployment"],
        )
        results = validate_role_contract(rc)
        assert any(r["status"] == "failed" and "task_types" in r["check"] for r in results)

    def test_unknown_preset_fails(self, valid_role_contract):
        results = validate_role_contract(
            valid_role_contract, known_presets=["repo_readonly"]
        )
        assert any(r["status"] == "failed" and "preset_exists" in r["check"] for r in results)

    def test_preserve_mode_requires_source_ref(self):
        rc = RoleContract(
            id="test",
            role_fidelity_mode=RoleFidelityMode.PRESERVE,
        )
        results = validate_role_contract(rc)
        assert any(r["status"] == "failed" and "source_ref" in r["check"] for r in results)

    def test_summarize_mode_no_source_ref_required(self):
        rc = RoleContract(
            id="test",
            role_fidelity_mode=RoleFidelityMode.SUMMARIZE,
        )
        results = validate_role_contract(rc)
        # Should not fail on source_ref for summarize mode
        source_ref_failures = [
            r for r in results
            if r["status"] == "failed" and "source_ref" in r["check"]
        ]
        assert len(source_ref_failures) == 0


class TestValidateHandoffContract:
    """validate_handoff_contract tests."""

    def test_valid_contract_passes(self, valid_handoff_contract, known_inventories):
        results = validate_handoff_contract(
            valid_handoff_contract,
            known_role_ids=known_inventories["role_ids"],
        )
        failed = [r for r in results if r["status"] == "failed"]
        assert len(failed) == 0, f"Expected 0 failures, got: {failed}"

    def test_empty_id_fails(self):
        hc = HandoffContractSchema(id="")
        results = validate_handoff_contract(hc)
        assert any(r["status"] == "failed" and "id" in r["check"] for r in results)

    def test_missing_validation_rule_fails(self):
        hc = HandoffContractSchema(
            id="test",
            required_fields=["risk_summary"],
            validation_rules=[],  # no rule for risk_summary
        )
        results = validate_handoff_contract(hc)
        assert any(r["status"] == "failed" and "required_fields_have_rules" in r["check"] for r in results)

    def test_from_roles_and_next_overlap_fails(self):
        hc = HandoffContractSchema(
            id="test",
            from_roles=["backend-developer"],
            allowed_next_roles=["backend-developer"],  # same role!
        )
        results = validate_handoff_contract(hc)
        assert any(r["status"] == "failed" and "self_handoff" in r["check"] for r in results)

    def test_unknown_role_reference_fails(self, valid_handoff_contract):
        results = validate_handoff_contract(
            valid_handoff_contract,
            known_role_ids=["orchestrator"],  # doesn't include backend-developer
        )
        assert any(r["status"] == "failed" and "roles_exist" in r["check"] for r in results)


class TestValidateTeamProposal:
    """validate_team_proposal tests."""

    def test_valid_proposal_passes(self, valid_proposal, known_inventories):
        results = validate_team_proposal(
            valid_proposal,
            known_team_ids=known_inventories["team_ids"],
            known_role_ids=known_inventories["role_ids"],
            known_presets=known_inventories["presets"],
            known_handoff_contracts=known_inventories["handoff_ids"],
        )
        failed = [r for r in results if r["status"] == "failed"]
        assert len(failed) == 0, f"Expected 0 failures, got: {failed}"

    def test_empty_goal_fails(self):
        tp = TeamProposal(goal="", recommended_team_id="test")
        results = validate_team_proposal(tp)
        assert any(r["status"] == "failed" and "goal" in r["check"] for r in results)

    def test_empty_team_id_fails(self):
        tp = TeamProposal(goal="build", recommended_team_id="")
        results = validate_team_proposal(tp)
        assert any(r["status"] == "failed" and "team_id" in r["check"] for r in results)

    def test_unknown_team_fails(self, valid_proposal):
        results = validate_team_proposal(
            valid_proposal,
            known_team_ids=["general-dev"],  # doesn't include saas-medium
        )
        assert any(r["status"] == "failed" and "team_exists" in r["check"] for r in results)

    def test_unknown_custom_role_fails(self):
        tp = TeamProposal(
            goal="build",
            recommended_team_id="saas-medium",
            rationale="test",
        )
        tp.customizations.agents = ["nonexistent-role"]
        results = validate_team_proposal(tp, known_role_ids=["orchestrator"])
        assert any(r["status"] == "failed" and "custom_roles_exist" in r["check"] for r in results)

    def test_unknown_preset_override_fails(self):
        tp = TeamProposal(
            goal="build",
            recommended_team_id="saas-medium",
            rationale="test",
        )
        tp.customizations.permission_overrides = {
            "orchestrator": "nonexistent_preset"
        }
        results = validate_team_proposal(
            tp,
            known_team_ids=["saas-medium"],
            known_presets=["repo_readonly"],
        )
        assert any(r["status"] == "failed" and "permission_overrides" in r["check"] for r in results)


class TestValidateAllCrossReferences:
    """validate_all_cross_references integration tests."""

    def test_valid_system_passes(self, known_inventories):
        team_contracts = [
            TeamContract(
                id="saas-medium",
                role_inventory=["frontend-developer", "security-reviewer"],
                permission_preset_mapping={
                    "frontend-developer": "frontend_worktree_rw",
                    "security-reviewer": "readonly_no_network",
                },
                handoff_contract_inventory=["sec-reviewer-handoff"],
            ),
        ]
        role_contracts = [
            RoleContract(
                id="frontend-developer",
                source=SourceProvenance(ref="v1.0.0"),
                permission_preset="frontend_worktree_rw",
                handoff_contract="sec-reviewer-handoff",
            ),
            RoleContract(
                id="security-reviewer",
                source=SourceProvenance(ref="v1.0.0"),
                permission_preset="readonly_no_network",
                handoff_contract="sec-reviewer-handoff",
            ),
            RoleContract(
                id="orchestrator",
                source=SourceProvenance(ref="v1.0.0"),
                permission_preset="orchestrator_safe",
            ),
        ]
        handoff_contracts = [
            HandoffContractSchema(
                id="sec-reviewer-handoff",
                from_roles=["frontend-developer"],
                allowed_next_roles=["orchestrator"],
            ),
        ]
        results = validate_all_cross_references(
            team_contracts, role_contracts, handoff_contracts,
            known_presets=known_inventories["presets"],
        )
        failed = [r for r in results if r["status"] == "failed"]
        assert len(failed) == 0, f"Expected 0 failures, got: {failed}"

    def test_orphan_handoff_detected(self, known_inventories):
        """A handoff contract not referenced by any role should fail."""
        team_contracts = [
            TeamContract(
                id="test",
                role_inventory=["orchestrator"],
                permission_preset_mapping={"orchestrator": "orchestrator_safe"},
                handoff_contract_inventory=["orphan-handoff"],
            ),
        ]
        role_contracts = [
            RoleContract(
                id="orchestrator",
                permission_preset="orchestrator_safe",
                handoff_contract="",  # references nothing
            ),
        ]
        handoff_contracts = [
            HandoffContractSchema(id="orphan-handoff"),
        ]
        results = validate_all_cross_references(
            team_contracts, role_contracts, handoff_contracts,
            known_presets=known_inventories["presets"],
        )
        orphan_failures = [
            r for r in results
            if r["status"] == "failed" and "referenced_by_role" in r["check"]
        ]
        assert len(orphan_failures) >= 1
