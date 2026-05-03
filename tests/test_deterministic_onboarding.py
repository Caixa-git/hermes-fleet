"""
Deterministic Onboarding Tests (v0.2+).

Tests that the same fixture inputs always produce the same validation
results. These are the foundation for the Deterministic Allocation
Tests category defined in WORKFLOW.md section 6.4.

All tests use fixture YAML files loaded from tests/fixtures/.
No real AI, Docker, or Hermes agent execution.
"""

from pathlib import Path

import pytest
import yaml

from hermes_fleet.contracts import (
    validate_team_contract,
    validate_role_contract,
    validate_handoff_contract,
    validate_team_proposal,
    validate_all_cross_references,
)
from hermes_fleet.policy import list_presets
from hermes_fleet.schema import (
    TeamContract,
    RoleContract,
    RoleFidelityMode,
    HandoffContractSchema,
    TeamProposal,
    TeamProposalCustomizations,
    SourceProvenance,
    ValidationRule,
    CompletionGate,
)
from hermes_fleet.teams import list_available_teams, load_team

FIXTURES_DIR = Path(__file__).resolve().parent / "fixtures"


# ──────────────────────────────────────────────
# Fixture loading helpers
# ──────────────────────────────────────────────


def load_fixture_yaml(name: str) -> dict:
    """Load a YAML fixture from tests/fixtures/."""
    path = FIXTURES_DIR / name
    if not path.exists():
        pytest.skip(f"Fixture not found: {path}")
    with open(path) as f:
        return yaml.safe_load(f)


def load_role_yaml(role_id: str) -> dict:
    """Load a role YAML from presets/roles/."""
    path = Path(__file__).resolve().parent.parent / "presets" / "roles" / f"{role_id}.yaml"
    if not path.exists():
        return {}
    with open(path) as f:
        return yaml.safe_load(f) or {}


# ──────────────────────────────────────────────
# Inventories (loaded from actual presets)
# ──────────────────────────────────────────────


@pytest.fixture(scope="module")
def known_role_ids():
    roles_dir = Path(__file__).resolve().parent.parent / "presets" / "roles"
    return sorted(f.stem for f in roles_dir.glob("*.yaml"))


@pytest.fixture(scope="module")
def known_presets():
    return list_presets()


@pytest.fixture(scope="module")
def known_team_ids():
    return list_available_teams()


# ──────────────────────────────────────────────
# Deterministic allocation tests
# ──────────────────────────────────────────────


class TestFixtureBasedValidation:
    """Tests that fixture-based validation is deterministic."""

    def test_saas_team_contract_validates_deterministically(
        self, known_role_ids, known_presets
    ):
        """Loading and validating the saas-medium fixture twice must give same results."""
        data = load_fixture_yaml("saas-medium-team-contract.yaml")
        tc = TeamContract(**data["team_contract"])

        results_a = validate_team_contract(
            tc,
            known_role_ids=known_role_ids,
            known_presets=known_presets,
            known_handoff_contracts=None,
        )
        results_b = validate_team_contract(
            tc,
            known_role_ids=known_role_ids,
            known_presets=known_presets,
            known_handoff_contracts=None,
        )
        assert results_a == results_b, "Validation results differ between runs"

    def test_security_reviewer_role_validates_deterministically(
        self, known_presets
    ):
        """Loading and validating the security-reviewer role twice must give same results."""
        data = load_fixture_yaml("security-reviewer-role-contract.yaml")
        rc = RoleContract(**data["role_contract"])

        results_a = validate_role_contract(rc, known_presets=known_presets)
        results_b = validate_role_contract(rc, known_presets=known_presets)
        assert results_a == results_b

    def test_handoff_contract_validates_deterministically(self, known_role_ids):
        """Loading and validating the handoff fixture twice must give same results."""
        data = load_fixture_yaml("security-reviewer-handoff-contract.yaml")
        hc = HandoffContractSchema(**data["handoff_contract"])

        results_a = validate_handoff_contract(hc, known_role_ids=known_role_ids)
        results_b = validate_handoff_contract(hc, known_role_ids=known_role_ids)
        assert results_a == results_b


class TestDeterministicProposal:
    """Tests that Team Proposals produce deterministic results."""

    def test_same_proposal_same_goal_deterministic(self):
        """Identical proposals with the same inputs must produce same validation."""
        tp_a = TeamProposal(
            goal="Build a SaaS MVP",
            recommended_team_id="saas-medium",
            rationale="test",
        )
        tp_b = TeamProposal(
            goal="Build a SaaS MVP",
            recommended_team_id="saas-medium",
            rationale="test",
        )
        results_a = validate_team_proposal(
            tp_a,
            known_team_ids=["saas-medium"],
            known_role_ids=["orchestrator"],
        )
        results_b = validate_team_proposal(
            tp_b,
            known_team_ids=["saas-medium"],
            known_role_ids=["orchestrator"],
        )
        assert results_a == results_b

    def test_different_proposal_different_result(self):
        """Different proposals should potentially produce different results."""
        tp_valid = TeamProposal(
            goal="Build a SaaS",
            recommended_team_id="saas-medium",
        )
        tp_invalid = TeamProposal(
            goal="Build a SaaS",
            recommended_team_id="nonexistent-team",
        )
        valid_results = validate_team_proposal(
            tp_valid, known_team_ids=["saas-medium"]
        )
        invalid_results = validate_team_proposal(
            tp_invalid, known_team_ids=["saas-medium"]
        )
        valid_failed = [r for r in valid_results if r["status"] == "failed"]
        invalid_failed = [r for r in invalid_results if r["status"] == "failed"]
        assert len(valid_failed) == 0
        assert len(invalid_failed) >= 1


class TestEndToEndWithPresets:
    """Tests that run validation against actual preset data."""

    def test_all_preset_roles_validate_against_real_presets(
        self, known_role_ids, known_presets
    ):
        """Every real role preset should pass basic contract validation."""
        for role_id in known_role_ids:
            role_data = load_role_yaml(role_id)
            if not role_data:
                continue
            rc = RoleContract(
                id=role_id,
                source=SourceProvenance(ref="v0.1"),  # presets have no upstream yet
                role_fidelity_mode=RoleFidelityMode.NEAR_VERBATIM,
                allowed_task_types=role_data.get("allowed_tasks", []),
                forbidden_task_types=role_data.get("forbidden_tasks", []),
                permission_preset=role_data.get(
                    "permission_preset", "repo_readonly"
                ),
            )
            results = validate_role_contract(
                rc,
                known_presets=known_presets,
                known_handoff_contracts=None,
            )
            failed = [r for r in results if r["status"] == "failed"]
            # Allow source_ref failure (v0.1 presets don't have upstream refs)
            real_failures = [
                r for r in failed
                if "source_ref" not in r["check"]
            ]
            assert len(real_failures) == 0, (
                f"Role '{role_id}' has validation failures: {real_failures}"
            )

    def test_all_teams_have_valid_role_references(
        self, known_role_ids, known_presets, known_team_ids
    ):
        """Every team's agents resolve against the known role inventory."""
        for team_id in known_team_ids:
            team_data = load_team(team_id)
            tc = TeamContract(
                id=team_id,
                role_inventory=team_data.get("agents", []),
                permission_preset_mapping={
                    agent: load_role_yaml(agent).get(
                        "permission_preset", "repo_readonly"
                    )
                    for agent in team_data.get("agents", [])
                },
            )
            results = validate_team_contract(
                tc,
                known_role_ids=known_role_ids,
                known_presets=known_presets,
                known_handoff_contracts=None,
            )
            failed = [r for r in results if r["status"] == "failed"]
            assert len(failed) == 0, (
                f"Team '{team_id}' has validation failures: {failed}"
            )
