"""
Tests: Contract schema validation (v0.2+).

These tests validate that the v0.2+ contract Pydantic models
accept valid data and reject invalid data according to their
schemas. No real AI, Docker, or Hermes agent execution.
"""

import pytest
from pydantic import ValidationError

from hermes_fleet.schema import (
    RoleFidelityMode,
    SourceProvenance,
    IdentityDriftGuard,
    ValidationRule,
    TeamProposalCustomizations,
    TeamProposal,
    HandoffContractSchema,
    RoleContract,
    TeamContract,
    CompletionGate,
)


class TestSourceProvenance:
    """SourceProvenance schema tests."""

    def test_defaults_are_empty(self):
        sp = SourceProvenance()
        assert sp.repository == ""
        assert sp.ref == ""
        assert sp.path == ""
        assert sp.hash == ""

    def test_all_fields_set(self):
        sp = SourceProvenance(
            repository="https://github.com/agency-agents/agency-agents",
            ref="v1.2.0",
            path="roles/security-reviewer.yaml",
            hash="sha256:a1b2c3d4e5f6",
        )
        assert sp.repository == "https://github.com/agency-agents/agency-agents"
        assert sp.ref == "v1.2.0"
        assert sp.path == "roles/security-reviewer.yaml"
        assert sp.hash == "sha256:a1b2c3d4e5f6"


class TestRoleFidelityMode:
    """RoleFidelityMode enum tests."""

    def test_preserve_is_default(self):
        """Preserve should be the default mode for all roles."""
        assert RoleFidelityMode.PRESERVE.value == "preserve"

    def test_all_modes_available(self):
        modes = [m.value for m in RoleFidelityMode]
        assert "preserve" in modes
        assert "near_verbatim" in modes
        assert "summarize" in modes

    def test_invalid_mode_rejected(self):
        with pytest.raises(ValidationError):
            RoleContract(id="test", role_fidelity_mode="invalid_mode")


class TestIdentityDriftGuard:
    """IdentityDriftGuard schema tests."""

    def test_default_questions_present(self):
        guard = IdentityDriftGuard()
        assert len(guard.pre_work) == 4
        assert len(guard.post_work) == 4
        assert "Is this task allowed for my role?" in guard.pre_work
        assert "Did I stay inside my role?" in guard.post_work

    def test_custom_questions(self):
        guard = IdentityDriftGuard(
            pre_work=["Custom pre-check"],
            post_work=["Custom post-check"],
        )
        assert guard.pre_work == ["Custom pre-check"]
        assert guard.post_work == ["Custom post-check"]


class TestValidationRule:
    """ValidationRule schema tests."""

    def test_required_field_default(self):
        rule = ValidationRule(field="risk_summary")
        assert rule.field == "risk_summary"
        assert rule.required is True

    def test_all_optional_fields(self):
        rule = ValidationRule(
            field="severity",
            required=True,
            min_length=1,
            max_length=50,
            enum=["critical", "high", "medium", "low"],
            min_items=1,
            regex=r"^[a-z]+$",
        )
        assert rule.enum == ["critical", "high", "medium", "low"]
        assert rule.min_length == 1
        assert rule.regex == r"^[a-z]+$"

    def test_field_is_required(self):
        with pytest.raises(ValidationError):
            ValidationRule()


class TestTeamProposal:
    """TeamProposal schema tests."""

    def test_minimal_proposal(self):
        proposal = TeamProposal(
            goal="Build a SaaS",
            recommended_team_id="saas-medium",
        )
        assert proposal.goal == "Build a SaaS"
        assert proposal.recommended_team_id == "saas-medium"
        assert proposal.rationale == ""
        assert proposal.customizations.agents == []

    def test_proposal_with_customizations(self):
        proposal = TeamProposal(
            goal="Build a SaaS",
            recommended_team_id="saas-medium",
            rationale="Good fit for the requirements",
            customizations=TeamProposalCustomizations(
                agents=["orchestrator", "backend-developer"],
                permission_overrides={"backend-developer": "backend_worktree_rw"},
            ),
        )
        assert len(proposal.customizations.agents) == 2
        assert proposal.customizations.permission_overrides["backend-developer"] == "backend_worktree_rw"

    def test_recommended_team_id_is_required(self):
        with pytest.raises(ValidationError):
            TeamProposal(goal="test")


class TestHandoffContractSchema:
    """HandoffContractSchema tests."""

    def test_minimal_handoff_contract(self):
        hc = HandoffContractSchema(id="security-reviewer_handoff")
        assert hc.id == "security-reviewer_handoff"
        assert hc.from_roles == []
        assert hc.required_fields == []

    def test_full_handoff_contract(self):
        hc = HandoffContractSchema(
            id="security-reviewer_handoff",
            from_roles=["backend-developer", "fullstack-developer"],
            allowed_next_roles=["orchestrator", "technical-writer"],
            required_fields=["risk_summary", "severity_labels", "approval_or_block"],
            validation_rules=[
                ValidationRule(field="risk_summary", required=True, min_length=50),
                ValidationRule(
                    field="severity_labels",
                    required=True,
                    enum=["critical", "high", "medium", "low", "info"],
                    min_items=1,
                ),
            ],
            completion_gate=CompletionGate(
                required=["explicit_approve_or_block", "no_code_modification"]
            ),
        )
        assert len(hc.from_roles) == 2
        assert len(hc.validation_rules) == 2
        assert "explicit_approve_or_block" in hc.completion_gate.required


class TestRoleContract:
    """RoleContract schema tests."""

    def test_minimal_role_contract(self):
        rc = RoleContract(id="security-reviewer")
        assert rc.id == "security-reviewer"
        assert rc.role_fidelity_mode == RoleFidelityMode.PRESERVE
        assert rc.source.repository == ""

    def test_role_contract_with_provenance(self):
        rc = RoleContract(
            id="security-reviewer",
            source=SourceProvenance(
                repository="https://github.com/agency-agents/agency-agents",
                ref="v1.2.0",
                path="roles/security-reviewer.yaml",
                hash="sha256:a1b2c3",
            ),
            role_fidelity_mode=RoleFidelityMode.PRESERVE,
            allowed_task_types=["security_review", "risk_analysis", "dependency_review"],
            forbidden_task_types=["implementation", "deployment"],
            permission_preset="readonly_no_network",
            handoff_contract="security-reviewer_handoff",
        )
        assert rc.source.ref == "v1.2.0"
        assert "security_review" in rc.allowed_task_types
        assert "implementation" in rc.forbidden_task_types
        assert rc.permission_preset == "readonly_no_network"

    def test_id_is_required(self):
        with pytest.raises(ValidationError):
            RoleContract()


class TestTeamContract:
    """TeamContract schema tests."""

    def test_minimal_team_contract(self):
        tc = TeamContract(id="saas-medium")
        assert tc.id == "saas-medium"
        assert tc.required_capabilities == []
        assert tc.role_inventory == []

    def test_full_team_contract(self):
        tc = TeamContract(
            id="saas-medium",
            required_capabilities=[
                "product_management", "frontend_development",
                "backend_development", "security_review",
            ],
            role_inventory=[
                "orchestrator", "product-manager", "frontend-developer",
                "backend-developer", "security-reviewer",
            ],
            permission_preset_mapping={
                "orchestrator": "orchestrator_safe",
                "product-manager": "docs_rw_repo_ro",
                "frontend-developer": "frontend_worktree_rw",
                "backend-developer": "backend_worktree_rw",
                "security-reviewer": "readonly_no_network",
            },
            handoff_contract_inventory=[
                "frontend-developer_to_reviewer",
                "backend-developer_to_security-reviewer",
            ],
        )
        assert len(tc.role_inventory) == 5
        assert tc.permission_preset_mapping["security-reviewer"] == "readonly_no_network"
        assert len(tc.handoff_contract_inventory) == 2
