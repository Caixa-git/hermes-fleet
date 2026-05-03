"""
Tests: Contract schemas and cross-reference validation.

Deterministic inline fixtures — no file I/O, no Docker, no AI.
Tests validate Pydantic model constraints and cross-reference logic
with pure data structures.
"""

import pytest
from pydantic import ValidationError

from hermes_fleet.contracts import (
    CrossReferenceResult,
    HandoffContract,
    RoleContract,
    TeamContract,
    validate_contract_cross_references,
)


# ──────────────────────────────────────────────
# Fixtures — valid contracts
# ──────────────────────────────────────────────


@pytest.fixture
def valid_team() -> TeamContract:
    return TeamContract(
        id="general-dev",
        name="General Development Team",
        description="A small general-purpose development team.",
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
        handoff={"required_outputs": ["task_status", "next_agent", "handoff_note"]},
        completion_gates={"required": ["task_assigned", "handoff_validated"]},
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
        handoff={"required_outputs": ["review_summary", "approval_status"]},
        completion_gates={"required": ["code_reviewed", "comments_documented"]},
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
            TeamContract(id="empty", name="Empty", description="", agents=[])

    def test_team_rejects_duplicate_agents(self):
        with pytest.raises(ValidationError, match="Duplicate agent"):
            TeamContract(
                id="dup",
                name="Dup",
                description="",
                agents=["orchestrator", "orchestrator"],
            )

    def test_team_optional_agents_defaults_to_empty(self, valid_team):
        assert valid_team.optional_agents == {}


# ──────────────────────────────────────────────
# Role Contract Tests
# ──────────────────────────────────────────────


class TestRoleContract:
    def test_valid_role_passes(self, valid_role_orchestrator):
        assert valid_role_orchestrator.id == "orchestrator"
        assert valid_role_orchestrator.permission_preset == "orchestrator_safe"

    def test_role_needs_at_least_one_allowed_task(self):
        with pytest.raises(ValidationError):
            RoleContract(
                id="no-tasks",
                name="No Tasks",
                description="",
                mission="",
                non_goals="",
                permission_preset="repo_readonly",
                allowed_tasks=[],
                handoff={"required_outputs": ["x"]},
                completion_gates={"required": ["y"]},
            )

    def test_role_rejects_empty_handoff_outputs(self):
        with pytest.raises(ValidationError, match="required_outputs"):
            RoleContract(
                id="no-handoff",
                name="No Handoff",
                description="",
                mission="",
                non_goals="",
                permission_preset="repo_readonly",
                allowed_tasks=["review"],
                handoff={"required_outputs": []},
                completion_gates={"required": ["y"]},
            )

    def test_role_rejects_empty_completion_gates(self):
        with pytest.raises(ValidationError, match="required gates"):
            RoleContract(
                id="no-gates",
                name="No Gates",
                description="",
                mission="",
                non_goals="",
                permission_preset="repo_readonly",
                allowed_tasks=["review"],
                handoff={"required_outputs": ["x"]},
                completion_gates={"required": []},
            )

    def test_role_allowed_commands_defaults_to_empty(self, valid_role_orchestrator):
        """Test that allowed_commands is optional and defaults to empty list."""
        role = RoleContract(
            id="minimal",
            name="Minimal",
            description="",
            mission="",
            non_goals="",
            permission_preset="repo_readonly",
            allowed_tasks=["review"],
            handoff={"required_outputs": ["summary"]},
            completion_gates={"required": ["reviewed"]},
        )
        assert role.allowed_commands == []


# ──────────────────────────────────────────────
# Handoff Contract Tests
# ──────────────────────────────────────────────


class TestHandoffContract:
    def test_valid_handoff_passes(self, valid_handoff):
        assert valid_handoff.id == "orchestrator_to_reviewer"
        assert "orchestrator" in valid_handoff.from_roles

    def test_handoff_needs_at_least_one_from_role(self):
        with pytest.raises(ValidationError):
            HandoffContract(
                id="bad",
                from_roles=[],
                allowed_next_roles=["reviewer"],
                required_fields=["summary"],
            )

    def test_handoff_needs_at_least_one_next_role(self):
        with pytest.raises(ValidationError):
            HandoffContract(
                id="bad",
                from_roles=["developer"],
                allowed_next_roles=[],
                required_fields=["summary"],
            )

    def test_handoff_needs_at_least_one_required_field(self):
        with pytest.raises(ValidationError):
            HandoffContract(
                id="bad",
                from_roles=["developer"],
                allowed_next_roles=["reviewer"],
                required_fields=[],
            )

    def test_handoff_rejects_self_handoff(self):
        with pytest.raises(ValidationError, match="both sender and receiver"):
            HandoffContract(
                id="self",
                from_roles=["developer"],
                allowed_next_roles=["developer"],
                required_fields=["summary"],
            )


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
            handoffs=[valid_handoff],
        )
        failures = [r for r in results if r.status == "failed"]
        assert not failures, f"Cross-reference failures: {failures}"

    def test_missing_agent_reference_fails(self, valid_role_orchestrator):
        """Team referencing a role that doesn't exist should fail."""
        team = TeamContract(
            id="bad-team",
            name="Bad Team",
            description="",
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
            handoff={"required_outputs": ["summary"]},
            completion_gates={"required": ["reviewed"]},
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
            handoffs=[handoff],
        )
        failures = [r for r in results if r.status == "failed"]
        assert len(failures) >= 1
        assert any("ghost-role" in r.message for r in failures)

    def test_duplicate_contract_ids_fails(self, valid_role_orchestrator):
        """Two contracts with the same ID should fail."""
        dup_role = RoleContract(
            id="orchestrator",  # same ID as valid_role_orchestrator
            name="Impostor",
            description="",
            mission="",
            non_goals="",
            permission_preset="repo_readonly",
            allowed_tasks=["review"],
            handoff={"required_outputs": ["summary"]},
            completion_gates={"required": ["reviewed"]},
        )
        results = validate_contract_cross_references(
            teams=[],
            roles=[valid_role_orchestrator, dup_role],
        )
        failures = [r for r in results if r.status == "failed"]
        assert len(failures) >= 1
        assert any("duplicate" in r.check.lower() for r in failures)

    def test_result_always_returned(self):
        """Even empty contract lists should produce progress results."""
        results = validate_contract_cross_references(
            teams=[TeamContract(id="t", name="T", description="", agents=["a"])],
            roles=[RoleContract(
                id="a", name="A", description="", mission="", non_goals="",
                permission_preset="p", allowed_tasks=["x"],
                handoff={"required_outputs": ["s"]},
                completion_gates={"required": ["g"]},
            )],
        )
        assert len(results) > 0


class TestFleetConfigContract:
    """FleetConfigContract schema validation."""

    def test_valid_fleet_config_passes(self):
        """A valid minimal fleet.yaml must pass validation."""
        from hermes_fleet.contracts import FleetConfigContract

        config = FleetConfigContract.model_validate({
            "fleet_version": "0.1.0",
            "name": "my-project",
            "team": "general-dev",
            "output_dir": ".fleet/generated",
        })
        assert config.team == "general-dev"
        assert config.name == "my-project"

    def test_defaults_are_set(self):
        """Empty fleet.yaml must use defaults without error."""
        from hermes_fleet.contracts import FleetConfigContract

        config = FleetConfigContract.model_validate({})
        assert config.team == "general-dev"
        assert config.name == "unnamed-fleet"
        assert config.output_dir == ".fleet/generated"

    def test_team_must_be_string(self):
        """Non-string team value must be rejected."""
        from hermes_fleet.contracts import FleetConfigContract

        with pytest.raises(ValidationError):
            FleetConfigContract.model_validate({"team": 123})

    def test_unknown_fields_are_ignored(self):
        """Extra unknown fields must not cause validation errors."""
        from hermes_fleet.contracts import FleetConfigContract

        config = FleetConfigContract.model_validate({
            "team": "saas-medium",
            "custom_field": "should be ignored",
        })
        assert config.team == "saas-medium"

    def test_fleet_config_from_dict_raises_on_bad_data(self):
        """fleet_config_from_dict must raise ContractValidationError for bad data."""
        from hermes_fleet.contracts import fleet_config_from_dict, ContractValidationError

        with pytest.raises(ContractValidationError):
            fleet_config_from_dict({"team": None})


class TestPermissionPresetContract:
    """PermissionPresetContract schema validation."""

    def test_valid_preset_passes(self):
        """A valid permission preset must pass validation."""
        from hermes_fleet.contracts import PermissionPresetContract

        preset = PermissionPresetContract.model_validate({
            "id": "test_preset",
            "allowed_workspaces": "readonly",
            "filesystem": {
                "writable_paths": [],
                "readonly_paths": ["**"],
                "forbidden_paths": [".env"],
            },
            "network_access": "none",
            "secret_allowlist": [],
        })
        assert preset.id == "test_preset"
        assert preset.network_access == "none"

    def test_minimal_preset_uses_defaults(self):
        """Missing optional fields must use defaults."""
        from hermes_fleet.contracts import PermissionPresetContract

        preset = PermissionPresetContract.model_validate({
            "id": "minimal",
            "allowed_workspaces": "kanban_only",
            "network_access": "control_plane_only",
        })
        assert preset.secret_allowlist == []
        assert preset.filesystem["readonly_paths"] == ["**"]

    def test_preset_needs_id(self):
        """Preset without id must be rejected."""
        from hermes_fleet.contracts import PermissionPresetContract

        with pytest.raises(ValidationError):
            PermissionPresetContract.model_validate({
                "allowed_workspaces": "readonly",
                "network_access": "none",
            })

    def test_permission_preset_from_dict_raises_on_bad_data(self):
        """permission_preset_from_dict must raise ContractValidationError for bad data."""
        from hermes_fleet.contracts import (
            ContractValidationError,
            permission_preset_from_dict,
        )

        with pytest.raises(ContractValidationError):
            permission_preset_from_dict({"id": "bad", "network_access": 123})

    def test_all_real_presets_pass_validation(self):
        """Every preset in presets/permissions/ must pass contract validation."""
        from pathlib import Path
        import yaml
        from hermes_fleet.contracts import permission_preset_from_dict

        presets_dir = Path(__file__).resolve().parent.parent / "presets" / "permissions"
        errors = []
        for f in sorted(presets_dir.glob("*.yaml")):
            with open(f) as fh:
                data = yaml.safe_load(fh) or {}
            try:
                permission_preset_from_dict(data)
            except Exception as e:
                errors.append(f"{f.name}: {e}")
        assert not errors, f"Preset validation errors: {errors}"
