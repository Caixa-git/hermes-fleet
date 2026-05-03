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

    def test_iphone_goal_recommends_iphone(self):
        team_id, _ = recommend_team("Build an iOS app with Swift")
        assert team_id == "iphone-app"

    def test_native_app_goal_recommends_iphone(self):
        team_id, _ = recommend_team("Create a native mobile app with push notifications")
        assert team_id == "iphone-app"

    def test_ai_goal_recommends_ai_app(self):
        team_id, _ = recommend_team("Build an AI chatbot with RAG")
        assert team_id == "ai-app"

    def test_ml_goal_recommends_ai_app(self):
        team_id, _ = recommend_team("Train and deploy an ML model")
        assert team_id == "ai-app"

    def test_security_goal_recommends_security_audit(self):
        team_id, _ = recommend_team("Conduct a security audit and penetration test")
        assert team_id == "security-audit"

    def test_compliance_goal_recommends_security_audit(self):
        team_id, _ = recommend_team("Run a compliance risk assessment")
        assert team_id == "security-audit"

    def test_research_goal_recommends_research_writing(self):
        team_id, _ = recommend_team("Write a research report on compiler design")
        assert team_id == "research-writing"

    def test_whitepaper_goal_recommends_research_writing(self):
        team_id, _ = recommend_team("Create a technical whitepaper")
        assert team_id == "research-writing"

    def test_content_goal_recommends_content_creator(self):
        team_id, _ = recommend_team("Develop a content marketing strategy")
        assert team_id == "content-creator"

    def test_blog_goal_recommends_content_creator(self):
        team_id, _ = recommend_team("Write SEO-optimized blog posts")
        assert team_id == "content-creator"

    def test_devops_goal_recommends_devops(self):
        team_id, _ = recommend_team("Set up CI/CD pipeline and infrastructure")
        assert team_id == "devops-deployment"

    def test_kubernetes_goal_recommends_devops(self):
        team_id, _ = recommend_team("Deploy to Kubernetes cluster")
        assert team_id == "devops-deployment"
