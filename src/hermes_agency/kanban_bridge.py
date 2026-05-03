"""Kanban Bridge — register Hermes Agency plans with Hermes Agent Kanban.

This module translates a PlanOutput (team + roles + task DAG) into
kanban_create() API calls. It is a v0.2+ feature.

Only available when running inside Hermes Agent (kanban_tools must be
importable). Falls back to dry-run mode otherwise.
"""

from __future__ import annotations

import json
import logging
import os

logger = logging.getLogger(__name__)


def _kanban_tools_available() -> bool:
    """Check if we're inside Hermes Agent with kanban tools."""
    return bool(os.environ.get("HERMES_KANBAN_TASK")) or _can_import_kanban()


def _can_import_kanban() -> bool:
    try:
        from tools.kanban_tools import _handle_create  # noqa: F401
        return True
    except ImportError:
        return False


def register_plan(plan_data: dict, dry_run: bool = False) -> list[dict]:
    """Register a plan's task DAG with Hermes Kanban.

    Args:
        plan_data: PlanOutput dict (from generator.generate_plan_output).
        dry_run: If True, return what would be created without creating.

    Returns:
        List of dicts with task_id, status for each created task.
    """
    plan = plan_data.get("plan", plan_data)
    agents_by_id = {a["role_id"]: a for a in plan.get("agents", [])}
    dag = plan.get("task_dag", [])

    if not dag:
        logger.warning("register_plan: empty task DAG, nothing to register")
        return []

    if not dry_run and not _kanban_tools_available():
        logger.warning(
            "Kanban tools not available. Run dry_run=True or execute "
            "inside Hermes Agent (HERMES_KANBAN_TASK must be set)."
        )
        return _dry_run_results(dag, agents_by_id, skipped=True)

    if dry_run:
        return _dry_run_results(dag, agents_by_id)

    return _execute_creates(dag, agents_by_id)


def _dry_run_results(
    dag: list[dict],
    agents_by_id: dict[str, dict],
    skipped: bool = False,
) -> list[dict]:
    """Return dry-run results without creating any tasks."""
    results = []
    for step in dag:
        agent = agents_by_id.get(step["assignee"], {})
        soul = agent.get("soul_md", "")[:100] + "..." if agent.get("soul_md") else ""
        results.append({
            "step": step["step"],
            "assignee": step["assignee"],
            "title": step["title"],
            "parents": step.get("parents", []),
            "skills": [soul] if soul else [],
            "workspace_kind": _workspace_for_role(step["assignee"]),
            "status": "dry_run" if not skipped else "unavailable",
        })
    return results


def _execute_creates(
    dag: list[dict],
    agents_by_id: dict[str, dict],
) -> list[dict]:
    """Execute kanban_create for each task in the DAG."""
    try:
        from tools.kanban_tools import _handle_create
    except ImportError as e:
        logger.error(f"Cannot import kanban tools: {e}")
        return [{"status": "error", "message": str(e)}]

    task_id_map: dict[str, str] = {}  # step_id -> kanban_task_id
    results = []

    for step in dag:
        step_id = step["step"]
        agent = agents_by_id.get(step["assignee"], {})
        skills = []
        if agent.get("soul_md"):
            skills.append(agent["soul_md"])
        if agent.get("policy_yaml"):
            skills.append(json.dumps(agent["policy_yaml"]))

        # Resolve parent kanban IDs
        parent_step_ids = step.get("parents", [])
        parent_ids = [
            task_id_map[p] for p in parent_step_ids if p in task_id_map
        ]

        try:
            result_json = _handle_create({
                "title": step["title"],
                "assignee": step["assignee"],
                "body": step.get("description", ""),
                "parents": parent_ids,
                "skills": skills,
                "workspace_kind": _workspace_for_role(step["assignee"]),
            })
            result = json.loads(result_json)
            if result.get("ok"):
                tid = result["task_id"]
                task_id_map[step_id] = tid
                results.append({
                    "step": step_id,
                    "kanban_task_id": tid,
                    "assignee": step["assignee"],
                    "title": step["title"],
                    "parents": parent_ids,
                    "status": "created",
                })
            else:
                results.append({
                    "step": step_id,
                    "status": "error",
                    "message": result.get("error", "unknown error"),
                })
        except Exception as e:
            logger.exception(f"Failed to create task {step_id}")
            results.append({
                "step": step_id,
                "status": "error",
                "message": str(e),
            })

    return results


def _workspace_for_role(role_id: str) -> str:
    """Determine Kanban workspace_kind from role.

    Maps permission presets to workspace kinds.
    """
    # Conservative defaults; Kanban's dispatcher resolves actual workspace.
    writer_roles = {
        "fullstack-developer", "frontend-developer", "backend-developer",
        "database-architect", "deployer",
    }
    if role_id in writer_roles:
        return "worktree"
    return "scratch"
