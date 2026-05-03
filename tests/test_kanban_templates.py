"""
Tests: Kanban template generation.
"""

from pathlib import Path

import pytest

from hermes_fleet.kanban import generate_kanban_templates


class TestKanbanTemplates:
    """Tests for Kanban handoff contract templates."""

    @pytest.fixture
    def templates(self):
        return generate_kanban_templates()

    def test_task_template_is_generated(self, templates):
        template = templates["task-template"]
        assert template is not None
        assert len(template) > 50

    def test_task_template_contains_required_fields(self, templates):
        template = templates["task-template"]
        assert "# Task Contract" in template
        assert "Task ID" in template
        assert "Goal" in template
        assert "Owner" in template
        assert "Required Outputs" in template
        assert "Next Agent" in template
        assert "Status" in template

    def test_handoff_template_is_generated(self, templates):
        template = templates["handoff-template"]
        assert template is not None
        assert len(template) > 50

    def test_handoff_template_contains_required_fields(self, templates):
        template = templates["handoff-template"]
        assert "# Handoff Note" in template
        assert "What I Did" in template
        assert "Files Changed" in template
        assert "Decisions Made" in template
        assert "Tests Run" in template
        assert "Known Risks" in template
        assert "Blockers" in template
        assert "Recommended Next Agent" in template
        assert "Handoff Checklist" in template

    def test_completion_gates_are_generated(self, templates):
        template = templates["completion-gates"]
        assert template is not None
        assert len(template) > 50

    def test_completion_gates_contain_required_sections(self, templates):
        template = templates["completion-gates"]
        assert "gates:" in template
        assert "task_scope:" in template
        assert "quality:" in template
        assert "handoff:" in template
        assert "security:" in template
        assert "identity:" in template

    def test_kanban_templates_dict(self, templates):
        assert "task-template" in templates
        assert "handoff-template" in templates
        assert "completion-gates" in templates
        assert len(templates["task-template"]) > 0
        assert len(templates["handoff-template"]) > 0
        assert len(templates["completion-gates"]) > 0

    def test_handoff_template_has_no_role_drift_checklist(self, templates):
        template = templates["handoff-template"]
        assert "No role drift" in template, "Handoff template must include role drift check"
        assert "Forbidden paths were not modified" in template

    def test_handoff_template_has_context_section(self, templates):
        """Context Handoff section is present and clearly optional."""
        template = templates["handoff-template"]
        assert "Context Handoff (optional)" in template
        assert "Decisions Considered" in template
        assert "Open Questions" in template
