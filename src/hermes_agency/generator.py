"""Generator — assemble and render plan output.

Generates SOUL.md (identity) and policy.yaml (boundaries) per agent role.
Does NOT generate Docker Compose, Kanban templates, or any execution artifacts.
"""

from pathlib import Path

import yaml

from hermes_agency.policy import compose_policy
from hermes_agency.teams import load_role
from hermes_agency.planner import plan_to_dag


def generate_plan_output(
    goal: str,
    team_id: str,
    team_def: dict,
    fleet_dir: Path | None = None,
) -> dict:
    """Generate a complete plan output dict.

    Returns a dict with team info, agent configs, and task DAG,
    ready to be serialized as YAML.
    """
    from hermes_agency.contracts import handoff_from_dict

    agents = team_def.get("agents", [])
    dag = plan_to_dag(goal, team_id, team_def)

    # Build agent configs
    agent_configs = []
    handoff_contracts = []

    for agent_id in agents:
        role_data = load_role(agent_id) or {}
        policy = compose_policy(agent_id)
        soul_md = _render_soul_md(agent_id, role_data, policy)

        agent_configs.append({
            "role_id": agent_id,
            "name": role_data.get("name", agent_id.replace("-", " ").title()),
            "description": role_data.get("description", ""),
            "permission_preset": role_data.get("permission_preset", "repo_readonly"),
            "soul_md": soul_md,
            "policy_yaml": policy,
        })

        # Handoff contract
        handoff = role_data.get("handoff", {})
        if handoff:
            handoff_contracts.append({
                "agent": agent_id,
                "required_outputs": handoff.get("required_outputs", []),
                "required_input": role_data.get("handoff_required_inputs", []),
            })

    plan_output = {
        "plan": {
            "goal": goal,
            "team_id": team_id,
            "team_name": team_def.get("name", team_id),
            "description": team_def.get("description", ""),
            "agents": agent_configs,
            "task_dag": dag,
            "handoff_contracts": handoff_contracts,
        }
    }

    return plan_output


def generate_agent_files(
    team_id: str,
    team_def: dict,
    output_dir: Path,
    force: bool = False,
) -> Path:
    """Generate SOUL.md and policy.yaml files for each agent.

    This is a file-based output (for human review or git tracking).
    Kanban-integrated output uses generate_plan_output() instead.
    """
    agents_dir = output_dir / "agents"
    agents_dir.mkdir(parents=True, exist_ok=True)

    agents = team_def.get("agents", [])
    for agent_id in agents:
        agent_dir = agents_dir / agent_id
        agent_dir.mkdir(parents=True, exist_ok=True)

        policy = compose_policy(agent_id)
        role_data = load_role(agent_id) or {}

        # SOUL.md
        soul_path = agent_dir / "SOUL.md"
        soul_content = _render_soul_md(agent_id, role_data, policy)
        _write_if_not_exists(soul_path, soul_content, force)

        # policy.yaml
        policy_path = agent_dir / "policy.yaml"
        policy_content = yaml.dump(policy, default_flow_style=False)
        _write_if_not_exists(policy_path, policy_content, force)

    return agents_dir


def _render_soul_md(agent_id: str, role_data: dict, policy: dict) -> str:
    """Render a SOUL.md from role data and policy."""
    name = role_data.get("name", agent_id.replace("-", " ").title())
    description = role_data.get("description", "")
    mission = role_data.get("mission", f"Execute assigned tasks for {name}.")
    non_goals = role_data.get("non_goals", "Exceed the defined role boundaries.")
    allowed_tasks = role_data.get("allowed_tasks", policy.get("task_policy", {}).get("allowed_task_types", []))
    forbidden_tasks = role_data.get("forbidden_tasks", policy.get("task_policy", {}).get("forbidden_task_types", []))
    writable_paths = policy.get("filesystem", {}).get("writable_paths", [])
    readonly_paths = policy.get("filesystem", {}).get("readonly_paths", ["**"])
    forbidden_paths = policy.get("filesystem", {}).get("forbidden_paths", [])
    network_mode = policy.get("network", {}).get("mode", "none")

    # Provenance metadata (v0.2+)
    source_repo = role_data.get("source_repository", "")
    source_ref = role_data.get("source_ref", "")
    source_path = role_data.get("source_path", "")
    source_hash = role_data.get("source_hash", "")
    provenance_lines = []
    if source_repo:
        provenance_lines.append(f"- **Source Repository**: {source_repo}")
    if source_ref:
        provenance_lines.append(f"- **Source Ref**: {source_ref}")
    if source_path:
        provenance_lines.append(f"- **Source Path**: {source_path}")
    if source_hash:
        provenance_lines.append(f"- **Source Hash**: {source_hash}")
    provenance_str = "\n".join(provenance_lines) if provenance_lines else "  *(local preset — no upstream provenance)*"

    allowed_tasks_str = "\n".join(f"- {t}" for t in allowed_tasks)
    forbidden_tasks_str = "\n".join(f"- {t}" for t in forbidden_tasks)
    writable_paths_str = "\n".join(f"- {p}" for p in writable_paths)
    readonly_paths_str = "\n".join(f"- {p}" for p in readonly_paths)
    forbidden_paths_str = "\n".join(f"- {p}" for p in forbidden_paths)

    return f"""# Identity

I am **{name}**.

*{description}*

My agent ID is `{agent_id}`.

---

# Mission

{mission}

---

# Non-Goals

I must not:
- {non_goals}

---

# Allowed Work

I may accept these task types:
{allowed_tasks_str}

---

# Forbidden Work

I must refuse or hand off these task types:
{forbidden_tasks_str}

---

# Allowed Filesystem Paths

I may write to:
{writable_paths_str}

I may read from:
{readonly_paths_str}

I must not access:
{forbidden_paths_str}

---

# Network

My network access mode is: **{network_mode}**

---

# Kanban Behavior

1. I receive tasks via task contracts.
2. I start work only after the task is assigned to me.
3. I document my progress in handoff notes.
4. When blocked, I create a blocker report.
5. When complete, I create a handoff note for the next agent.

---

# Handoff Contract

Before handing off work, I must include:
- Summary of what was done
- Files changed
- Decisions made
- Tests run
- Known risks or blockers
- Recommended next agent

---

# Output Format

All handoffs must include a complete handoff note.
All tasks must document:
- What was accomplished
- What was not accomplished
- Why (if incomplete)

---

# Failure Behavior

If blocked:
- Document the blocker in detail
- Notify the orchestrator
- Preserve partial work

If I receive a task outside my role:
- Refuse politely with explanation
- Recommend the correct agent

If I detect missing permissions:
- Stop the current action
- Report the missing permission
- Do not attempt to work around it

|---

# Provenance

{provenance_str}

---

# Identity Drift Self-Check

## Before Starting
- [ ] Is this task allowed for my role?
- [ ] Do I have the required context?
- [ ] Do I have permission for the requested action?
- [ ] Should this be handed off to another agent?

## Before Completing
- [ ] Did I stay inside my role?
- [ ] Did I touch only allowed paths?
- [ ] Did I produce required outputs?
- [ ] Did I leave a clear handoff?
"""


def _write_if_not_exists(path: Path, content: str, force: bool):
    """Write a file if it doesn't exist, or if force is True."""
    try:
        rel = path.relative_to(Path.cwd())
    except ValueError:
        rel = path
    if path.exists() and not force:
        print(f"  [skip] {rel}")
        return
    path.write_text(content)
    print(f"  [write] {rel}")
