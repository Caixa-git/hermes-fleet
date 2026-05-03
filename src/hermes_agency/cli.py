"""Hermes Agency CLI — v0.1

Commands:
  init              Create local .fleet configuration
  plan <goal>       Analyze goal and recommend team + task DAG
  apply             Register plan with Hermes Kanban (v0.2+)
"""

from pathlib import Path
from datetime import datetime
from typing import Optional

import typer
import yaml

from hermes_agency.planner import recommend_team, plan_to_dag
from hermes_agency.generator import generate_plan_output

app = typer.Typer(
    name="hermes-agency",
    help="From goal to team — where Kanban meets agency-agents.",
    add_completion=True,
)


def _get_fleet_dir(project_dir: Path) -> Path:
    return project_dir / ".fleet"


def _ensure_fleet_dir(project_dir: Path) -> Path:
    fleet_dir = _get_fleet_dir(project_dir)
    fleet_dir.mkdir(parents=True, exist_ok=True)
    (fleet_dir / "plan").mkdir(exist_ok=True)
    (fleet_dir / "plan" / "agents").mkdir(exist_ok=True)
    return fleet_dir


# ── Init ─────────────────────────────────────────────────────────────


@app.command()
def init(
    directory: Optional[str] = typer.Option(
        None, "--dir", "-d", help="Project directory (default: current directory)"
    ),
):
    """Initialize Hermes Agency in a project directory."""
    project_dir = Path(directory).resolve() if directory else Path.cwd()
    fleet_dir = _ensure_fleet_dir(project_dir)

    fleet_yaml_path = fleet_dir / "fleet.yaml"

    if fleet_yaml_path.exists():
        print("[yellow]⚠ fleet.yaml already exists. Skipping.[/yellow]")
    else:
        default_config = {
            "agency_version": "0.1.0",
            "name": project_dir.name,
            "team": "general-dev",
        }
        with open(fleet_yaml_path, "w") as f:
            yaml.dump(default_config, f, default_flow_style=False)
        print(f"[green]✓ Initialized Hermes Agency in {project_dir}[/green]")
        print(f"  Created: {fleet_yaml_path}")

    # Create lock files
    foundation_lock = fleet_dir / "foundation.lock.yaml"
    agency_lock = fleet_dir / "agency.lock.yaml"
    today = datetime.now().strftime("%Y-%m-%d")

    if not foundation_lock.exists():
        lock_data = {
            "foundation_version": 1,
            "sources": [
                {"id": "agent_oriented_planning", "version": "v1", "locked_at": today},
                {"id": "llm_mas_survey", "version": "v1", "locked_at": today},
                {"id": "nist_rbac", "version": "v1", "locked_at": today},
                {"id": "contract_net_protocol", "version": "v1", "locked_at": today},
            ],
        }
        with open(foundation_lock, "w") as f:
            yaml.dump(lock_data, f, default_flow_style=False)
        print(f"  Created: {foundation_lock}")

    if not agency_lock.exists():
        lock_data = {
            "agency_version": 1,
            "ref": "v0.1.0",
            "locked_at": today,
        }
        with open(agency_lock, "w") as f:
            yaml.dump(lock_data, f, default_flow_style=False)
        print(f"  Created: {agency_lock}")

    print(
        "\nNext steps:\n"
        f"  hermes-agency plan \"<your goal>\"  — Recommend a team + task DAG\n"
    )


# ── Plan ─────────────────────────────────────────────────────────────


@app.command()
def plan(
    goal: str = typer.Argument(..., help="What do you want to build?"),
    show_details: bool = typer.Option(
        False, "--show-details", help="Show full agent roster with permissions"
    ),
    output: Optional[str] = typer.Option(
        None, "--output", "-o", help="Write plan as YAML to file"
    ),
):
    """Analyze a goal and recommend a team with task DAG."""
    from hermes_agency.teams import load_team, load_role

    team_id, team_def = recommend_team(goal)
    agents = team_def.get("agents", [])
    dag = plan_to_dag(goal, team_id, team_def)

    # Print plan
    print(f"\n[bold]Goal:[/bold] {goal}")
    print(f"[bold]Team:[/bold] {team_id} — {team_def.get('description', '')}")
    print(f"[bold]Agents:[/bold] {len(agents)}")
    for agent_id in agents:
        role_data = load_role(agent_id) or {}
        name = role_data.get("name", agent_id.replace("-", " ").title())
        preset = role_data.get("permission_preset", "default")
        print(f"  {agent_id}: {name} [{preset}]")

    print(f"\n[bold]Task DAG:[/bold] {len(dag)} steps")
    for step in dag:
        deps = f" (depends: {', '.join(step['parents'])})" if step["parents"] else ""
        print(f"  {step['step']}. [{step['assignee']}] {step['title']}{deps}")

    # Generate full output
    plan_output = generate_plan_output(goal, team_id, team_def, fleet_dir=_get_fleet_dir(Path.cwd()))

    if output:
        output_path = Path(output)
        output_path.parent.mkdir(parents=True, exist_ok=True)
        with open(output_path, "w") as f:
            yaml.dump(plan_output, f, default_flow_style=False, sort_keys=False)
        print(f"\n[green]✓ Plan written to {output_path}[/green]")
    else:
        # Write to .fleet/plan/plan.yaml by default
        plan_dir = _get_fleet_dir(Path.cwd()) / "plan"
        plan_dir.mkdir(parents=True, exist_ok=True)
        plan_path = plan_dir / "plan.yaml"
        with open(plan_path, "w") as f:
            yaml.dump(plan_output, f, default_flow_style=False, sort_keys=False)
        print(f"\n[green]✓ Plan saved to {plan_path}[/green]")

    print("\nNext:\n"
          f"  hermes-agency apply  — Register plan with Kanban (v0.2+)")


# ── Apply (v0.2+ placeholder) ────────────────────────────────────────


@app.command()
def apply(
    plan_file: Optional[str] = typer.Option(
        None, "--plan", "-p", help="Plan YAML file (default: .fleet/plan/plan.yaml)"
    ),
    dry_run: bool = typer.Option(
        False, "--dry-run", help="Show what would be created without creating"
    ),
):
    """Register a plan with Hermes Agent Kanban. (v0.2+)"""
    project_dir = Path.cwd()
    plan_path = Path(plan_file) if plan_file else _get_fleet_dir(project_dir) / "plan" / "plan.yaml"

    if not plan_path.exists():
        print(f"[red]✗ No plan found at {plan_path}[/red]")
        print("  Run 'hermes-agency plan \"<goal>\"' first.")
        raise typer.Exit(1)

    with open(plan_path) as f:
        plan_data = yaml.safe_load(f) or {}

    print("[yellow]⚠ apply is not yet implemented (planned for v0.2+).[/yellow]")
    print(f"\n[bold]Would create {len(plan_data.get('task_dag', []))} Kanban tasks:[/bold]")
    for step in plan_data.get("task_dag", []):
        deps = f" (depends: {', '.join(step['parents'])})" if step.get("parents") else ""
        print(f"  {step['step']}. [{step['assignee']}] {step['title']}{deps}")
    print("\nEach task would receive:")
    print("  - assignee = agent role")
    print("  - skills = [SOUL.md + policy.yaml]")
    print("  - parents = dependency edges")
    print("  - workspace_kind from permission preset")


if __name__ == "__main__":
    app()
