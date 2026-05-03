"""Tests: Contract schemas and cross-reference validation.

Deterministic inline fixtures -- no file I/O, no Docker, no AI.
Tests validate Pydantic model constraints and cross-reference logic
with pure data structures.
"""

import pytest
from pydantic import ValidationError

from hermes_agency.contracts import (
    CheckResult,
    HandoffContract,
    RoleContract,
    TeamContract,
    validate_contract_cross_references,
)


# ──────────────────────────────────────────────
# Fixtures -- valid contracts
# ──────────────────────────────────────────────


@pytest.fixture
def valid_team() -> TeamContract:
    return TeamContract(
        id="general-dev",
        name="General Development Team",
        agents=["orchestrator", "reviewer"],
    )


@pytest.fixture
def valid_role_orchestrator() -> RoleContract:
    return RoleContract(
        id="orchestrator",
        name="Orchestrator",
        description="Manages Kanban board, tasks, and handoffs.",
        mission="Coordinate the fleet.",
        non_goals="Writing application source code.",
        permission_preset="orchestrator_safe",
        allowed_tasks=["orchestration", "task_assignment", "blocker_resolution"],
        forbidden_tasks=["implementation", "deployment"],
        allowed_commands=["cat", "ls", "grep"],
        denied_commands=["git push", "docker", "pip"],
        handoff_required_outputs=["task_status", "next_agent", "handoff_note"],
        completion_gates_required=["task_assigned", "handoff_validated"],
    )


@pytest.fixture
def valid_role_reviewer() -> RoleContract:
    return RoleContract(
        id="reviewer",
        name="Reviewer",
        description="Reviews code for quality and correctness.",
        mission="Ensure code quality and consistency.",
        non_goals="Writing application code.",
        permission_preset="repo_readonly",
        allowed_tasks=["code_review", "style_check", "architecture_review"],
        forbidden_tasks=["implementation", "deployment"],
        handoff_required_outputs=["review_summary", "approval_status"],
        completion_gates_required=["code_reviewed", "comments_documented"],
    )


@pytest.fixture
def valid_handoff() -> HandoffContract:
    return HandoffContract(
        id="orchestrator_to_reviewer",
        from_roles=["orchestrator"],
        allowed_next_roles=["reviewer"],
        required_fields=["summary", "files_changed", "test_results"],
    )


@pytest.fixture
def known_presets() -> list[str]:
    return ["orchestrator_safe", "repo_readonly", "readonly_no_network"]


# ──────────────────────────────────────────────
# Team Contract Tests
# ──────────────────────────────────────────────


class TestTeamContract:
    def test_valid_team_passes(self, valid_team):
        assert valid_team.id == "general-dev"
        assert len(valid_team.agents) >= 1

    def test_team_needs_at_least_one_agent(self):
        with pytest.raises(ValidationError):
            TeamContract(id="empty", name="Empty", agents=[])

    def test_team_optional_agents_defaults_to_empty(self, valid_team):
        assert valid_team.optional_agents == []


# ──────────────────────────────────────────────
# Role Contract Tests
# ──────────────────────────────────────────────


class TestRoleContract:
    def test_valid_role_passes(self, valid_role_orchestrator):
        assert valid_role_orchestrator.id == "orchestrator"
        assert valid_role_orchestrator.permission_preset == "orchestrator_safe"

    def test_role_allowed_commands_defaults_to_empty(self, valid_role_orchestrator):
        role = RoleContract(
            id="minimal",
            name="Minimal",
            description="",
            mission="",
            non_goals="",
            permission_preset="repo_readonly",
            allowed_tasks=["review"],
            handoff_required_outputs=["summary"],
            completion_gates_required=["reviewed"],
        )
        assert role.allowed_commands == []

    def test_role_empty_handoff_outputs_allowed(self):
        """Empty handoff outputs should be valid (not all roles need handoff)."""
        role = RoleContract(
            id="simple",
            name="Simple",
            description="",
            mission="",
            non_goals="",
            permission_preset="repo_readonly",
            allowed_tasks=["review"],
        )
        assert role.handoff_required_outputs == []

    def test_role_empty_completion_gates_allowed(self):
        role = RoleContract(
            id="simple",
            name="Simple",
            description="",
            mission="",
            non_goals="",
            permission_preset="repo_readonly",
            allowed_tasks=["review"],
        )
        assert role.completion_gates_required == []

    def test_role_accepts_handoff_contract_reference(self):
        role = RoleContract(
            id="with-ref",
            name="With Handoff Ref",
            description="",
            mission="",
            non_goals="",
            permission_preset="repo_readonly",
            allowed_tasks=["review"],
            handoff_contract="developer-reviewer",
        )
        assert role.handoff_contract == "developer-reviewer"

    def test_role_accepts_provenance_metadata(self):
        role = RoleContract(
            id="provenance-test",
            name="Provenance Test",
            description="",
            mission="",
            non_goals="",
            permission_preset="repo_readonly",
            allowed_tasks=["review"],
            source_repository="https://github.com/example/agency-agents",
            source_ref="abc123def456",
            source_path="roles/reviewer.yaml",
            source_hash="sha256:deadbeef",
        )
        assert role.source_repository == "https://github.com/example/agency-agents"
        assert role.source_hash == "sha256:deadbeef"


# ──────────────────────────────────────────────
# Handoff Contract Tests
# ──────────────────────────────────────────────


class TestHandoffContract:
    def test_valid_handoff_passes(self, valid_handoff):
        assert valid_handoff.id == "orchestrator_to_reviewer"
        assert "orchestrator" in valid_handoff.from_roles

    def test_handoff_empty_from_roles_allowed(self):
        """Empty from_roles is valid -- the contract may define generic handoff."""
        hc = HandoffContract(
            id="generic",
            from_roles=[],
            allowed_next_roles=["orchestrator"],
            required_fields=["summary"],
        )
        assert hc.from_roles == []

    def test_handoff_empty_next_roles_allowed(self):
        hc = HandoffContract(
            id="sink",
            from_roles=["developer"],
            allowed_next_roles=[],
            required_fields=["summary"],
        )
        assert hc.allowed_next_roles == []

    def test_handoff_validation_rules(self):
        hc = HandoffContract(
            id="with-rules",
            from_roles=["developer"],
            allowed_next_roles=["reviewer"],
            required_fields=["summary", "status"],
            validation_rules=[
                {"field": "summary", "required": True, "min_length": 10},
                {"field": "status", "required": True, "enum": ["pass", "fail"]},
            ],
        )
        assert len(hc.validation_rules) == 2
        assert hc.validation_rules[0].field == "summary"

    def test_handoff_completion_gate(self):
        hc = HandoffContract(
            id="with-gate",
            from_roles=["developer"],
            allowed_next_roles=["reviewer"],
            required_fields=["summary"],
            completion_gate_required=["review_started"],
        )
        assert "review_started" in hc.completion_gate_required


# ──────────────────────────────────────────────
# Cross-Reference Validation Tests
# ──────────────────────────────────────────────


class TestCrossReferenceValidation:
    def test_all_references_pass(self, valid_team, valid_role_orchestrator,
                                  valid_role_reviewer, known_presets):
        """Valid contracts with matching references should all pass."""
        results = validate_contract_cross_references(
            teams=[valid_team],
            roles=[valid_role_orchestrator, valid_role_reviewer],
            known_presets=known_presets,
        )
        failures = [r for r in results if r.status == "failed"]
        assert not failures, f"Cross-reference failures: {failures}"

    def test_all_references_pass_with_handoffs(self, valid_team,
                                                valid_role_orchestrator,
                                                valid_role_reviewer,
                                                valid_handoff):
        """Valid contracts including handoffs should all pass."""
        results = validate_contract_cross_references(
            teams=[valid_team],
            roles=[valid_role_orchestrator, valid_role_reviewer],
            known_presets=["orchestrator_safe", "repo_readonly"],
            handoff_contracts={valid_handoff.id: valid_handoff},
        )
        failures = [r for r in results if r.status == "failed"]
        assert not failures, f"Cross-reference failures: {failures}"

    def test_missing_agent_reference_fails(self, valid_role_orchestrator):
        """Team referencing a role that doesn't exist should fail."""
        team = TeamContract(
            id="bad-team",
            name="Bad Team",
            agents=["orchestrator", "nonexistent-role"],
        )
        results = validate_contract_cross_references(
            teams=[team],
            roles=[valid_role_orchestrator],
        )
        failures = [r for r in results if r.status == "failed"]
        assert len(failures) >= 1
        assert any("nonexistent-role" in r.message for r in failures)

    def test_missing_permission_preset_fails(self, valid_role_orchestrator):
        """Role referencing an unknown preset should fail."""
        bad_role = RoleContract(
            id="bad-role",
            name="Bad Role",
            description="",
            mission="",
            non_goals="",
            permission_preset="nonexistent_preset",
            allowed_tasks=["review"],
            handoff_required_outputs=["summary"],
            completion_gates_required=["reviewed"],
        )
        results = validate_contract_cross_references(
            teams=[],
            roles=[bad_role],
            known_presets=["repo_readonly"],
        )
        failures = [r for r in results if r.status == "failed"]
        assert len(failures) >= 1
        assert any("nonexistent_preset" in r.message for r in failures)

    def test_missing_handoff_role_reference_fails(self, valid_role_orchestrator):
        """Handoff referencing a non-existent role should fail."""
        handoff = HandoffContract(
            id="bad-handoff",
            from_roles=["orchestrator"],
            allowed_next_roles=["ghost-role"],
            required_fields=["summary"],
        )
        results = validate_contract_cross_references(
            teams=[],
            roles=[valid_role_orchestrator],
            known_presets=["orchestrator_safe"],
            handoff_contracts={handoff.id: handoff},
        )
        failures = [r for r in results if r.status == "failed"]
        assert len(failures) >= 1
        assert any("ghost-role" in r.message for r in failures)

    def test_result_always_returned(self):
        """Even empty contract lists should produce progress results."""
        results = validate_contract_cross_references(
            teams=[TeamContract(id="t", name="T", agents=["a"])],
            roles=[RoleContract(
                id="a", name="A", description="", mission="", non_goals="",
                permission_preset="p", allowed_tasks=["x"],
                handoff_required_outputs=["s"],
                completion_gates_required=["g"],
            )],
            known_presets=["p"],
        )
        assert len(results) > 0

    def test_role_to_handoff_ref_passes(self, valid_role_orchestrator):
        """A role referencing an existing handoff contract should pass."""
        handoff = HandoffContract(
            id="orchestrator-developer",
            from_roles=["orchestrator"],
            allowed_next_roles=["reviewer"],
            required_fields=["task_description", "acceptance_criteria"],
        )
        role = RoleContract(
            id="orchestrator",
            name="Orchestrator with Handoff Ref",
            description="",
            mission="",
            non_goals="",
            permission_preset="orchestrator_safe",
            allowed_tasks=["orchestration"],
            handoff_contract="orchestrator-developer",
            handoff_required_outputs=["task_status"],
            completion_gates_required=["done"],
        )
        reviewer = RoleContract(
            id="reviewer", name="Reviewer", description="", mission="",
            non_goals="", permission_preset="repo_readonly",
            allowed_tasks=["review"],
        )
        results = validate_contract_cross_references(
            teams=[],
            roles=[role, reviewer],
            known_presets=["orchestrator_safe", "repo_readonly"],
            handoff_contracts={handoff.id: handoff},
        )
        failures = [r for r in results if r.status == "failed"]
        assert not failures, f"Unexpected failures: {[(r.check, r.message) for r in failures]}"

    def test_role_to_handoff_ref_fails(self, valid_role_orchestrator):
        """A role referencing a non-existent handoff contract should fail."""
        role = RoleContract(
            id="orchestrator",
            name="Orchestrator with Bad Ref",
            description="",
            mission="",
            non_goals="",
            permission_preset="orchestrator_safe",
            allowed_tasks=["orchestration"],
            handoff_contract="nonexistent-handoff",
        )
        results = validate_contract_cross_references(
            teams=[],
            roles=[role],
            known_presets=["orchestrator_safe"],
            handoff_contracts={},
        )
        failures = [r for r in results if r.status == "failed"]
        assert len(failures) >= 1
        assert any("nonexistent-handoff" in r.message for r in failures)

    def test_handoff_from_role_unknown_fails(self):
        """Handoff referencing a role not in the role list should fail."""
        handoff = HandoffContract(
            id="bad-from",
            from_roles=["alien-role"],
            allowed_next_roles=["reviewer"],
            required_fields=["summary"],
        )
        reviewer = RoleContract(
            id="reviewer", name="Reviewer", description="", mission="",
            non_goals="", permission_preset="repo_readonly",
            allowed_tasks=["review"],
        )
        results = validate_contract_cross_references(
            teams=[], roles=[reviewer],
            known_presets=["repo_readonly"],
            handoff_contracts={handoff.id: handoff},
        )
        failures = [r for r in results if r.status == "failed"]
        assert any("alien-role" in r.message for r in failures)


class TestHandoffRequiredFieldsValidation:
    """v0.3: Every handoff contract must define at least one required_field."""

    def test_handoff_with_required_fields_passes(self):
        """Handoff contract with required_fields should pass validation."""
        from hermes_agency.contracts import (
            HandoffContract,
            RoleContract,
            validate_contract_cross_references,
        )
        hc = HandoffContract(
            id="valid-handoff",
            from_roles=["orchestrator"],
            allowed_next_roles=["reviewer"],
            required_fields=["summary", "status"],
        )
        role = RoleContract(
            id="orchestrator", name="O", description="", mission="",
            non_goals="", permission_preset="p", allowed_tasks=["x"],
            handoff_required_outputs=["s"], completion_gates_required=["g"],
        )
        results = validate_contract_cross_references(
            teams=[], roles=[role], known_presets=["p"],
            handoff_contracts={hc.id: hc},
        )
        failures = [r for r in results if r.status == "failed"]
        required_field_failures = [r for r in failures if "required_fields" in r.check]
        assert len(required_field_failures) == 0, \
            f"Handoff with required_fields should not fail: {required_field_failures}"

    def test_handoff_without_required_fields_fails(self):
        """Handoff contract without required_fields should fail validation."""
        from hermes_agency.contracts import (
            HandoffContract,
            RoleContract,
            validate_contract_cross_references,
        )
        hc = HandoffContract(
            id="bad-handoff",
            from_roles=["orchestrator"],
            allowed_next_roles=["reviewer"],
            required_fields=[],
        )
        role = RoleContract(
            id="orchestrator", name="O", description="", mission="",
            non_goals="", permission_preset="p", allowed_tasks=["x"],
            handoff_required_outputs=["s"], completion_gates_required=["g"],
        )
        results = validate_contract_cross_references(
            teams=[], roles=[role], known_presets=["p"],
            handoff_contracts={hc.id: hc},
        )
        failures = [r for r in results if r.status == "failed"]
        required_field_failures = [r for r in failures if "required_fields" in r.check]
        assert len(required_field_failures) >= 1
        assert any("bad-handoff" in r.message for r in required_field_failures)


# ──────────────────────────────────────────────
# FleetConfig Contract Tests
# ──────────────────────────────────────────────


class TestFleetConfigContract:
    """FleetConfigContract schema validation."""

    def test_valid_config(self):
        from hermes_agency.contracts import fleet_config_from_dict
        data = {
            "fleet_version": "0.1.0",
            "name": "test-fleet",
            "team": "general-dev",
        }
        cfg = fleet_config_from_dict(data)
        assert cfg.fleet_version == "0.1.0"
        assert cfg.name == "test-fleet"
        assert cfg.team == "general-dev"

    def test_default_output_dir(self):
        from hermes_agency.contracts import fleet_config_from_dict
        data = {
            "fleet_version": "0.1.0",
            "name": "test",
            "team": "general-dev",
        }
        cfg = fleet_config_from_dict(data)
        assert cfg.output_dir == ".fleet/generated"

    def test_empty_fleet_version_fails(self):
        from hermes_agency.contracts import fleet_config_from_dict
        data = {
            "fleet_version": "",
            "name": "test",
            "team": "general-dev",
        }
        with pytest.raises(ValidationError):
            fleet_config_from_dict(data)


# ──────────────────────────────────────────────
# PermissionPreset Contract Tests
# ──────────────────────────────────────────────


class TestPermissionPresetContract:
    """PermissionPresetContract schema validation."""

    def test_valid_preset(self):
        from hermes_agency.contracts import permission_preset_from_dict
        data = {
            "preset_id": "test_preset",
            "workspace": "readonly",
            "repo_write": False,
            "secrets": [],
            "network": "none",
        }
        preset = permission_preset_from_dict(data)
        assert preset.preset_id == "test_preset"
        assert preset.workspace == "readonly"

    def test_empty_id_fails(self):
        from hermes_agency.contracts import permission_preset_from_dict
        with pytest.raises(ValidationError):
            permission_preset_from_dict({"preset_id": "  "})


# ──────────────────────────────────────────────
# Handoff Contract from Dict Tests
# ──────────────────────────────────────────────


class TestHandoffFromDict:
    """handoff_from_dict conversion and validation."""

    def test_basic_conversion(self):
        from hermes_agency.contracts import handoff_from_dict
        data = {
            "id": "test-handoff",
            "from_roles": ["developer"],
            "allowed_next_roles": ["reviewer"],
            "required_fields": ["summary"],
        }
        hc = handoff_from_dict(data)
        assert hc.id == "test-handoff"

    def test_with_validation_rules(self):
        from hermes_agency.contracts import handoff_from_dict
        data = {
            "id": "test",
            "from_roles": ["dev"],
            "allowed_next_roles": ["rev"],
            "required_fields": ["summary"],
            "validation_rules": [
                {"field": "summary", "required": True, "min_length": 10},
            ],
            "completion_gate": {"required": ["gate1"]},
        }
        hc = handoff_from_dict(data)
        assert len(hc.validation_rules) == 1
        assert hc.completion_gate_required == ["gate1"]

    def test_empty_id_fails(self):
        from hermes_agency.contracts import handoff_from_dict
        with pytest.raises(ValidationError):
            handoff_from_dict({"id": "", "from_roles": [], "allowed_next_roles": [], "required_fields": []})


# ──────────────────────────────────────────────
# Cross-Reference Validation Invariants
# ──────────────────────────────────────────────


class TestCrossReferenceInvariants:
    """Invariant tests for cross-reference validation behavior."""

    def test_empty_contracts_no_crash(self):
        """Even with empty lists, the function should not crash."""
        results = validate_contract_cross_references(teams=[], roles=[])
        assert isinstance(results, list)

    def test_all_results_have_check_name(self):
        """Every CheckResult must have a non-empty check name."""
        team = TeamContract(id="t", name="T", agents=["a"])
        role = RoleContract(
            id="a", name="A", description="", mission="", non_goals="",
            permission_preset="p", allowed_tasks=["x"],
            handoff_required_outputs=["s"],
            completion_gates_required=["g"],
        )
        results = validate_contract_cross_references(teams=[team], roles=[role], known_presets=["p"])
        for r in results:
            assert r.check, f"Empty check name in result: {r}"

    def test_handoff_contracts_none_skips_handoff_checks(self):
        """When handoff_contracts is None, no handoff-related checks appear."""
        team = TeamContract(id="t", name="T", agents=["a"])
        role = RoleContract(
            id="a", name="A", description="", mission="", non_goals="",
            permission_preset="p", allowed_tasks=["x"],
        )
        results = validate_contract_cross_references(
            teams=[team], roles=[role], known_presets=["p"],
        )
        handoff_checks = [r for r in results if "handoff" in r.check]
        assert all(r.status == "passed" for r in handoff_checks)

    def test_check_result_type(self):
        """Verify CheckResult is the correct type."""
        r = CheckResult("passed", "test-check")
        assert r.status == "passed"
        assert r.check == "test-check"
        assert r.message == ""
