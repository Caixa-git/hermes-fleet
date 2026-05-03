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

    def test_soul_contains_identity_section(self):
        """SOUL.md must include Identity section."""
        soul = self._render_soul("orchestrator")
        assert "# Identity" in soul

    def test_soul_contains_mission_section(self):
        soul = self._render_soul("orchestrator")
        assert "# Mission" in soul

    def test_soul_contains_non_goals_section(self):
        soul = self._render_soul("orchestrator")
        assert "# Non-Goals" in soul

    def test_soul_contains_allowed_work_section(self):
        soul = self._render_soul("orchestrator")
        assert "# Allowed Work" in soul

    def test_soul_contains_forbidden_work_section(self):
        soul = self._render_soul("orchestrator")
        assert "# Forbidden Work" in soul

    def test_soul_contains_filesystem_paths_section(self):
        soul = self._render_soul("orchestrator")
        assert "Allowed Filesystem Paths" in soul

    def test_soul_contains_network_section(self):
        soul = self._render_soul("orchestrator")
        assert "Network" in soul

    def test_soul_contains_kanban_section(self):
        soul = self._render_soul("orchestrator")
        assert "Kanban Behavior" in soul

    def test_soul_contains_handoff_section(self):
        soul = self._render_soul("orchestrator")
        assert "Handoff Contract" in soul

    def test_soul_contains_failure_behavior(self):
        soul = self._render_soul("orchestrator")
        assert "Failure Behavior" in soul

    def test_soul_contains_identity_drift_self_check(self):
        soul = self._render_soul("orchestrator")
        assert "Identity Drift Self-Check" in soul
        assert "Before Starting" in soul
        assert "Before Completing" in soul

    def test_security_reviewer_has_no_code_modification_check(self):
        soul = self._render_soul("security-reviewer")
        assert "no_code_modification" in soul.lower() or "identity drift" in soul.lower()

    def test_soul_mentions_agent_id(self):
        soul = self._render_soul("frontend-developer")
        assert "frontend-developer" in soul
