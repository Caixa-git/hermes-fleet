"""
Tests: Planner recommendations.
"""

import pytest

from hermes_fleet.planner import recommend_team


class TestPlanner:
    """Tests for the goal-to-team planner."""

    def test_saas_goal_recommends_saas(self):
        team_id, team_def = recommend_team("Build a medium-sized SaaS MVP")
        assert team_id == "saas-medium"
        assert team_def is not None

    def test_subscription_goal_recommends_saas(self):
        team_id, _ = recommend_team("Build a subscription-based platform")
        assert team_id == "saas-medium"

    def test_dashboard_goal_recommends_saas(self):
        team_id, _ = recommend_team("Create a customer dashboard with billing")
        assert team_id == "saas-medium"

    def test_generic_goal_recommends_general_dev(self):
        team_id, team_def = recommend_team("Build a simple CLI tool")
        assert team_id == "general-dev"

    def test_empty_goal_defaults_to_general_dev(self):
        team_id, _ = recommend_team("")
        assert team_id == "general-dev"

    def test_api_goal_recommends_saas(self):
        team_id, _ = recommend_team("Build a public API with authentication")
        assert team_id == "saas-medium"

    def test_marketplace_goal_recommends_saas(self):
        team_id, _ = recommend_team("Create an online marketplace")
        assert team_id == "saas-medium"

    def test_team_def_has_agents(self):
        _, team_def = recommend_team("Refactor this Python project")
        assert "agents" in team_def
        assert len(team_def["agents"]) >= 3
