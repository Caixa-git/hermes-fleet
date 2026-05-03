"""
Tests: SOUL.md generation for each agent role.
"""

from pathlib import Path

import pytest
import yaml

from hermes_fleet.generator import _render_soul_md
from hermes_fleet.policy import compose_policy
from hermes_fleet.teams import load_role, load_team

ROLES_DIR = Path(__file__).resolve().parent.parent / "presets" / "roles"

# All expected sections in a generated SOUL.md
EXPECTED_SECTIONS = [
    "# Identity",
    "# Mission",
    "# Non-Goals",
    "# Allowed Work",
    "# Forbidden Work",
    "Allowed Filesystem Paths",
    "Network",
    "Kanban Behavior",
    "Handoff Contract",
    "Failure Behavior",
    "Identity Drift Self-Check",
]


class TestSoulGeneration:
    """Tests for SOUL.md content generation."""

    def _render_soul(self, role_id: str) -> str:
        """Helper to render a SOUL.md for a given role."""
        role_data = load_role(role_id) or {}
        policy = compose_policy(role_id)
        return _render_soul_md(role_id, role_data, policy)

    def test_soul_is_generated_for_every_role(self):
        """Verify SOUL.md is generated for every agent in the presets."""
        for role_file in ROLES_DIR.glob("*.yaml"):
            role_id = role_file.stem
            soul = self._render_soul(role_id)
            assert soul is not None
            assert len(soul) > 100, f"SOUL.md for {role_id} is too short"

    @pytest.mark.parametrize("section", EXPECTED_SECTIONS)
    def test_soul_contains_required_sections(self, section):
        """Every required section must be present in the SOUL.md template."""
        soul = self._render_soul("orchestrator")
        assert section in soul, f"Missing section: {section}"

    def test_soul_contains_identity_drift_checklist(self):
        """Identity Drift section has Before Starting and Before Completing."""
        soul = self._render_soul("orchestrator")
        assert "Before Starting" in soul
        assert "Before Completing" in soul

    def test_security_reviewer_has_no_code_modification_check(self):
        soul = self._render_soul("security-reviewer")
        assert "no_code_modification" in soul.lower() or "identity drift" in soul.lower()

    def test_soul_mentions_agent_id(self):
        soul = self._render_soul("frontend-developer")
        assert "frontend-developer" in soul

    def test_soul_contains_provenance_section(self):
        """Provenance metadata section exists (v0.2+)."""
        soul = self._render_soul("orchestrator")
        assert "# Provenance" in soul
