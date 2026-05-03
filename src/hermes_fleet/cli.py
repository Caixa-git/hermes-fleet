"""
Hermes Fleet CLI — v0.1

Commands:
  init              Create local .fleet configuration
  plan <goal>       Recommend a team for a goal
  generate          Generate agent configurations
  test safe-defaults  Validate generated configurations
"""

from pathlib import Path
from typing import Optional

import typer
from rich.console import Console
from rich.panel import Panel
from rich.table import Table

from hermes_fleet.planner import recommend_team
from hermes_fleet.generator import generate_fleet
from hermes_fleet.safe_defaults import run_safe_defaults_check

app = typer.Typer(
    name="hermes-fleet",
    help="A secure team bootstrapper for isolated Hermes Agent fleets.",
    add_completion=True,
)
console = Console()


def _get_fleet_dir(project_dir: Path) -> Path:
    """Return the .fleet directory for the given project directory."""
    return project_dir / ".fleet"


def _ensure_fleet_dir(project_dir: Path) -> Path:
    """Create and return the .fleet directory."""
    fleet_dir = _get_fleet_dir(project_dir)
    fleet_dir.mkdir(parents=True, exist_ok=True)
    (fleet_dir / "generated").mkdir(exist_ok=True)
    return fleet_dir


@app.command()
def init(
    directory: Optional[str] = typer.Option(
        None, "--dir", "-d", help="Project directory (default: current directory)"
    ),
):
    """Initialize Hermes Fleet in a project directory."""
    project_dir = Path(directory).resolve() if directory else Path.cwd()
    fleet_dir = _ensure_fleet_dir(project_dir)

    fleet_yaml_path = fleet_dir / "fleet.yaml"

    if fleet_yaml_path.exists():
        console.print("[yellow]⚠ fleet.yaml already exists. Skipping.[/yellow]")
    else:
        default_config = {
            "fleet_version": "0.1.0",
            "name": project_dir.name,
            "team": "general-dev",
            "output_dir": ".fleet/generated",
        }
        import yaml

        with open(fleet_yaml_path, "w") as f:
            yaml.dump(default_config, f, default_flow_style=False)

        console.print(
            f"[green]✓ Initialized Hermes Fleet in {project_dir}[/green]"
        )
        console.print(f"  Created: {fleet_yaml_path}")

    # Create generated subdirectories
    (fleet_dir / "generated" / "agents").mkdir(parents=True, exist_ok=True)
    (fleet_dir / "generated" / "kanban").mkdir(parents=True, exist_ok=True)

    console.print(
        "\nNext steps:\n"
        f"  hermes-fleet plan \"<your goal>\"  — Recommend a team\n"
        f"  hermes-fleet generate             — Generate agent configs\n"
        f"  hermes-fleet test safe-defaults   — Validate safe defaults"
    )


@app.command()
def plan(
    goal: str = typer.Argument(..., help="What do you want to build?"),
    show_details: bool = typer.Option(
        False, "--show-details", help="Show full agent roster with permissions"
    ),
):
    """Analyze a goal and recommend a team."""
    from hermes_fleet.teams import load_team

    team_id, team_def = recommend_team(goal)

    console.print(Panel.fit(
        f"[bold cyan]Recommended team:[/bold cyan] [green]{team_id}[/green]\n\n"
        f"[bold]Goal:[/bold] {goal}\n"
        f"[bold]Description:[/bold] {team_def.get('description', '')}",
        title="Hermes Fleet Plan",
    ))

    # Show agents
    agents = team_def.get("agents", [])
    table = Table(title=f"Team: {team_id} ({len(agents)} agents)")
    table.add_column("Agent", style="cyan")
    table.add_column("Role", style="white")
    if show_details:
        table.add_column("Network", style="yellow")
        table.add_column("Workspace", style="magenta")
        table.add_column("Secrets", style="dim")

    for agent_id in agents:
        role_data = _load_role(agent_id)
        if show_details:
            table.add_row(
                agent_id,
                role_data.get("name", agent_id),
                role_data.get("network_access", "none"),
                role_data.get("allowed_workspaces", "readonly"),
                str(role_data.get("secret_allowlist", [])),
            )
        else:
            table.add_row(agent_id, role_data.get("name", agent_id))

    console.print(table)

    # Show defaults note
    console.print(
        "\n[dim]Defaults:[/dim]\n"
        "[dim]  - Each agent runs in its own Docker container[/dim]\n"
        "[dim]  - Each agent has its own /opt/data[/dim]\n"
        "[dim]  - Reviewers are read-only[/dim]\n"
        "[dim]  - Security reviewers have no network[/dim]\n"
        "[dim]  - Deployer is disabled by default[/dim]\n"
        "[dim]  - Production secrets are not injected[/dim]\n"
        "[dim]  - Kanban handoff contracts are enabled[/dim]\n"
        "\n"
        "[bold]Next:[/bold] hermes-fleet generate"
    )


def _load_role(role_id: str) -> dict:
    """Load a role preset by ID. Delegates to teams.load_role."""
    from hermes_fleet.teams import load_role

    role = load_role(role_id)
    return role if role else {"name": role_id.replace("-", " ").title()}


@app.command()
def generate(
    team: Optional[str] = typer.Option(
        None, "--team", help="Override team selection"
    ),
    force: bool = typer.Option(
        False, "--force", help="Overwrite existing generated files"
    ),
):
    """Generate all agent configuration files."""
    import yaml

    # Read fleet config
    project_dir = Path.cwd()
    fleet_yaml_path = _get_fleet_dir(project_dir) / "fleet.yaml"

    if not fleet_yaml_path.exists():
        console.print(
            "[red]✗ No fleet.yaml found. Run 'hermes-fleet init' first.[/red]"
        )
        raise typer.Exit(1)

    with open(fleet_yaml_path) as f:
        fleet_config = yaml.safe_load(f) or {}

    selected_team = team or fleet_config.get("team", "general-dev")

    # Load team
    from hermes_fleet.teams import load_team

    team_def = load_team(selected_team)
    if not team_def:
        console.print(
            f"[red]✗ Unknown team: {selected_team}[/red]\n"
            f"  Available teams: general-dev, saas-medium"
        )
        raise typer.Exit(1)

    # Cross-reference validation: all agents must have role definitions
    from hermes_fleet.teams import load_role

    agents = team_def.get("agents", [])
    missing_roles = [a for a in agents if load_role(a) is None]
    if missing_roles:
        console.print(
            f"[red]✗ Team '{selected_team}' references unknown roles: "
            f"{', '.join(missing_roles)}[/red]"
        )
        raise typer.Exit(1)

    # Cross-reference validation: all role permission_presets must resolve
    from hermes_fleet.teams import _get_presets_dir

    presets_dir = _get_presets_dir()
    known_presets = {p.stem for p in (presets_dir / "permissions").glob("*.yaml")}
    bad_presets = []
    for agent_id in agents:
        role_data = load_role(agent_id)
        preset = role_data.get("permission_preset", "")
        if preset and preset not in known_presets:
            bad_presets.append(f"{agent_id} → '{preset}'")
    if bad_presets:
        console.print(
            "[red]✗ Unknown permission preset(s):[/red]"
        )
        for bp in bad_presets:
            console.print(f"  [red]  {bp}[/red]")
        raise typer.Exit(1)

    # Generate
    output_dir = generate_fleet(
        project_dir=project_dir,
        team_id=selected_team,
        team_def=team_def,
        force=force,
    )

    console.print(f"\n[green]✓ Generated fleet configuration in: {output_dir}[/green]")
    console.print(
        "\nFiles created:\n"
        f"  {output_dir}/docker-compose.generated.yaml\n"
        f"  {output_dir}/agents/<agent-id>/SOUL.md\n"
        f"  {output_dir}/agents/<agent-id>/policy.yaml\n"
        f"  {output_dir}/kanban/\n"
        "\nNext: hermes-fleet test safe-defaults"
    )


test_app = typer.Typer(
    name="test",
    help="Run validation checks against generated configurations.",
    add_completion=False,
)
app.add_typer(test_app, name="test")


@test_app.command("safe-defaults")
def test_safe_defaults(
    verbose: bool = typer.Option(
        False, "--verbose", "-v", help="Show all checks including passing"
    ),
):
    """Validate generated configuration against safe-default rules."""
    project_dir = Path.cwd()
    generated_dir = _get_fleet_dir(project_dir) / "generated"

    if not generated_dir.exists():
        generated_dir = Path.cwd() / ".fleet" / "generated"

    if not generated_dir.exists():
        console.print(
            f"[red]✗ No generated output found at {generated_dir}[/red]\n"
            f"  Run 'hermes-fleet generate' first."
        )
        raise typer.Exit(1)

    results = run_safe_defaults_check(generated_dir, verbose=verbose)

    passed = sum(1 for r in results if r["status"] == "passed")
    failed = sum(1 for r in results if r["status"] == "failed")
    skipped = sum(1 for r in results if r["status"] == "skipped")

    console.print(f"\nSafe-defaults validation results:")
    console.print(f"  Passed: {passed}")
    console.print(f"  Failed: {failed}")
    console.print(f"  Skipped: {skipped}")

    for r in results:
        if r["status"] == "failed":
            console.print(f"  [red]✗ {r['check']}: {r['message']}[/red]")
        elif verbose and r["status"] == "passed":
            console.print(f"  [green]✓ {r['check']}[/green]")
        elif verbose and r["status"] == "skipped":
            console.print(f"  [dim]… {r['check']}: {r['message']}[/dim]")

    if failed > 0:
        console.print(f"\n[red]Safe-defaults check FAILED.[/red]")
        raise typer.Exit(1)
    console.print(f"\n[green]All safe-defaults checks PASSED.[/green]")


def main():
    """Entry point for the CLI."""
    app()


if __name__ == "__main__":
    main()
