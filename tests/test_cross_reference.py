"""
Cross-Reference Validation Tests (v0.2+).

These tests validate that all references between presets resolve
correctly. No team, role, or permission preset should reference
a target that does not exist.

All tests are pure validation — they load preset YAML files and
check cross-references. No existing v0.1 code is modified.
"""

from pathlib import Path

import pytest
import yaml

from hermes_fleet.teams import list_available_teams, load_team
from hermes_fleet.policy import list_presets

PRESETS_DIR = Path(__file__).resolve().parent.parent / "presets"
ROLES_DIR = PRESETS_DIR / "roles"


def _load_role_yaml(role_id: str) -> dict:
    """Load a role YAML file and return its dict."""
    path = ROLES_DIR / f"{role_id}.yaml"
    if not path.exists():
        return {}
    with open(path) as f:
        return yaml.safe_load(f) or {}


def _all_role_ids() -> list[str]:
    """Return all available role IDs from the presets/roles directory."""
    return sorted(f.stem for f in ROLES_DIR.glob("*.yaml"))


class TestTeamToRoleCrossReferences:
    """Every role referenced by a team must exist as a role file."""

    def test_all_team_roles_exist(self):
        """Every agent listed in a team preset must have a corresponding role file."""
        role_ids = _all_role_ids()
        for team_id in list_available_teams():
            team = load_team(team_id)
            assert team is not None, f"Team {team_id} could not be loaded"
            for agent_id in team.get("agents", []):
                assert agent_id in role_ids, (
                    f"Team '{team_id}' references agent '{agent_id}' "
                    f"but no matching role file exists in presets/roles/"
                )

    def test_no_missing_role_files(self):
        """Each team's role_inventory agents are a subset of available role files."""
        role_ids = _all_role_ids()
        for team_id in list_available_teams():
            team = load_team(team_id)
            for agent_id in team.get("agents", []):
                assert agent_id in role_ids, (
                    f"Missing role file for '{agent_id}' "
                    f"(referenced by team '{team_id}')"
                )


class TestRolePermissionPresetReferences:
    """Every permission preset referenced by a role must exist."""

    def test_all_role_permission_presets_exist(self):
        """Every role's permission_preset must be a known preset."""
        known_presets = list_presets()
        for role_id in _all_role_ids():
            role = _load_role_yaml(role_id)
            preset_id = role.get("permission_preset")
            if preset_id:
                assert preset_id in known_presets, (
                    f"Role '{role_id}' references unknown permission preset "
                    f"'{preset_id}'. Known presets: {known_presets}"
                )

    def test_default_preset_is_known(self):
        """If a role has no explicit permission_preset, the default must exist."""
        known_presets = list_presets()
        # The default is "repo_readonly" in compose_policy()
        default = "repo_readonly"
        assert default in known_presets, (
            f"Default permission preset '{default}' not found in known presets"
        )


class TestRoleHandoffReferences:
    """Every handoff contract referenced by a role should be noted."""

    def test_role_handoff_fields_are_defined(self):
        """Each role should have at minimum a handoff section with required_outputs."""
        for role_id in _all_role_ids():
            role = _load_role_yaml(role_id)
            handoff = role.get("handoff")
            if handoff is None:
                pytest.skip(f"Role '{role_id}' has no handoff section (optional in v0.1)")
                continue
            required = handoff.get("required_outputs", [])
            assert len(required) > 0, (
                f"Role '{role_id}' has handoff section but no required_outputs"
            )


class TestTeamConsistency:
    """Teams should have consistent internal references."""

    def test_all_teams_have_unique_ids(self):
        """Team IDs must be unique across all team presets."""
        team_ids = list_available_teams()
        assert len(team_ids) == len(set(team_ids)), (
            "Duplicate team IDs found"
        )

    def test_team_agents_have_no_duplicates(self):
        """A team should not list the same agent twice."""
        for team_id in list_available_teams():
            team = load_team(team_id)
            agents = team.get("agents", [])
            assert len(agents) == len(set(agents)), (
                f"Team '{team_id}' has duplicate agents: {agents}"
            )

    def test_role_ids_have_no_duplicates(self):
        """Role IDs must be unique across all role files."""
        role_ids = _all_role_ids()
        assert len(role_ids) == len(set(role_ids)), (
            "Duplicate role IDs found"
        )


class TestSafetyInvariantPresets:
    """Safety invariants that must hold for all presets (cross-reference)."""

    def test_security_reviewer_has_no_network(self):
        """Security reviewer role must have network_access: none."""
        role = _load_role_yaml("security-reviewer")
        preset_id = role.get("permission_preset", "repo_readonly")
        assert preset_id in ("readonly_no_network",), (
            f"Security reviewer has permission_preset '{preset_id}', "
            f"expected 'readonly_no_network'"
        )

    def test_reviewer_has_readonly_preset(self):
        """Reviewer role must use a read-only permission preset."""
        role = _load_role_yaml("reviewer")
        preset_id = role.get("permission_preset", "")
        read_only_presets = {"repo_readonly", "readonly_no_network"}
        assert preset_id in read_only_presets, (
            f"Reviewer has permission_preset '{preset_id}', "
            f"expected one of {read_only_presets}"
        )

    def test_orchestrator_uses_orchestrator_safe(self):
        """Orchestrator role must use orchestrator_safe preset."""
        role = _load_role_yaml("orchestrator")
        preset_id = role.get("permission_preset", "")
        assert preset_id == "orchestrator_safe", (
            f"Orchestrator has permission_preset '{preset_id}', "
            f"expected 'orchestrator_safe'"
        )


class TestNoOrphanRoles:
    """Roles that exist but are not used by any team (informational)."""

    def test_all_role_files_are_used_by_at_least_one_team(self):
        """Every role file should be referenced by at least one team."""
        role_ids = set(_all_role_ids())
        used_roles = set()
        for team_id in list_available_teams():
            team = load_team(team_id)
            used_roles.update(team.get("agents", []))
        orphaned = role_ids - used_roles
        # v0.1 has exactly 11 roles, all used by at least one team
        assert len(orphaned) == 0, (
            f"Orphaned role files (not used by any team): {sorted(orphaned)}"
        )
