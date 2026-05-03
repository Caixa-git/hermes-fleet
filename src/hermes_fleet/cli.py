"""Hermes Fleet CLI — v0.2

Commands:
  init              Create local .fleet configuration
  plan <goal>       Recommend a team for a goal
  generate          Generate agent configurations
  validate          Validate all preset contracts and cross-references
  test safe-defaults  Validate generated configurations
  customize         Customize fleet configuration (roles, permissions, resources)
"""

from pathlib import Path
from datetime import datetime
from typing import Optional

import typer
import yaml
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
            "fleet_version": "0.2.0",
            "name": project_dir.name,
            "team": "general-dev",
            "output_dir": ".fleet/generated",
            "resources": {
                "default_cpu": "0.5",
                "default_memory": "512M",
            },
        }

        with open(fleet_yaml_path, "w") as f:
            yaml.dump(default_config, f, default_flow_style=False)

        console.print(
            f"[green]✓ Initialized Hermes Fleet in {project_dir}[/green]"
        )
        console.print(f"  Created: {fleet_yaml_path}")

    # Create generated subdirectories
    (fleet_dir / "generated" / "agents").mkdir(parents=True, exist_ok=True)
    (fleet_dir / "generated" / "kanban").mkdir(parents=True, exist_ok=True)

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
        console.print(f"  Created: {foundation_lock}")

    if not agency_lock.exists():
        lock_data = {
            "agency_version": 1,
            "ref": "v0.1.0",
            "locked_at": today,
        }
        with open(agency_lock, "w") as f:
            yaml.dump(lock_data, f, default_flow_style=False)
        console.print(f"  Created: {agency_lock}")

    console.print(
        "\nNext steps:\n"
        f"  hermes-fleet plan \"<your goal>\"  — Recommend a team\n"
        f"  hermes-fleet validate            — Validate all preset contracts\n"
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
            f"[red]✗ Fleet references unknown roles: "
            f"{', '.join(missing_roles)}[/red]\n"
            f"  Run 'hermes-fleet validate' for full diagnostics."
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
        console.print("  Run 'hermes-fleet validate' for full diagnostics.")
        raise typer.Exit(1)

    # Generate
    output_dir = generate_fleet(
        project_dir=project_dir,
        team_id=selected_team,
        team_def=team_def,
        force=force,
        resources=fleet_config.get("resources"),
    )

    console.print(f"\n[green]✓ Generated fleet configuration in: {output_dir}[/green]")
    console.print(
        "\nFiles created:\n"
        f"  {output_dir}/docker-compose.generated.yaml\n"
        f"  {output_dir}/agents/<agent-id>/SOUL.md\n"
        f"  {output_dir}/agents/<agent-id>/policy.yaml\n"
        f"  {output_dir}/kanban/\n"
        "Next: hermes-fleet test safe-defaults or hermes-fleet validate"
    )


@app.command()
def validate(
    verbose: bool = typer.Option(
        False, "--verbose", "-v", help="Show all checks including passing"
    ),
):
    """Validate all preset contracts and cross-references."""
    from hermes_fleet.contracts import (
        team_from_dict,
        role_from_dict,
        handoff_from_dict,
        CheckResult,
        validate_contract_cross_references,
    )
    from hermes_fleet.teams import (
        _get_presets_dir,
        list_available_teams,
        list_available_roles,
        load_team,
        load_role,
        list_available_handoffs,
        load_handoff,
    )

    presets_dir = _get_presets_dir()
    known_presets = [p.stem for p in (presets_dir / "permissions").glob("*.yaml")]

    # Load all teams
    teams = []
    for team_id in list_available_teams():
        data = load_team(team_id)
        if data is not None:
            teams.append(team_from_dict(data))

    # Load all roles
    roles = []
    for role_id in list_available_roles():
        data = load_role(role_id)
        if data is not None:
            roles.append(role_from_dict(data))

    # Load all handoff contracts
    handoffs_dict = {}
    for hid in list_available_handoffs():
        data = load_handoff(hid)
        if data is not None:
            hc = handoff_from_dict(data)
            handoffs_dict[hc.id] = hc

    # Run cross-reference validation
    from hermes_fleet.checks import run_role_adoption_gate as _run_gate
    results = validate_contract_cross_references(
        teams, roles, known_presets=known_presets, handoff_contracts=handoffs_dict
    )

    # Three-pillar role adoption gate
    raw_roles = []
    for role_id in list_available_roles():
        data = load_role(role_id)
        if data is not None:
            raw_roles.append(data)
    pillar_results = _run_gate(raw_roles, set(known_presets))
    results.extend(
        CheckResult(
            status=r["status"],
            check=r["check"],
            message=r.get("message", ""),
        )
        for r in pillar_results
    )

    # Lock file checks — only if .fleet/ exists (project context)
    from hermes_fleet.contracts import FoundationLock, AgencyLock
    fleet_dir = _get_fleet_dir(Path.cwd())

    if fleet_dir.exists():
        foundation_path = fleet_dir / "foundation.lock.yaml"
        agency_path = fleet_dir / "agency.lock.yaml"

        if not foundation_path.exists():
            results.append(CheckResult("failed", "lock:foundation", "foundation.lock.yaml not found — run 'hermes-fleet init'"))
        else:
            with open(foundation_path) as f:
                FoundationLock(**yaml.safe_load(f))
            results.append(CheckResult("passed", "lock:foundation"))

        if not agency_path.exists():
            results.append(CheckResult("failed", "lock:agency", "agency.lock.yaml not found — run 'hermes-fleet init'"))
        else:
            with open(agency_path) as f:
                AgencyLock(**yaml.safe_load(f))
            results.append(CheckResult("passed", "lock:agency"))

    passed = sum(1 for r in results if r.status == "passed")
    failed = sum(1 for r in results if r.status == "failed")

    console.print("\nPreset contract validation results:")
    console.print(f"  Contracts loaded: {len(teams)} teams, {len(roles)} roles, {len(handoffs_dict)} handoffs")
    console.print(f"  Passed: {passed}")
    console.print(f"  Failed: {failed}")

    for r in results:
        if r.status == "failed":
            console.print(f"  [red]✗ {r.check}: {r.message}[/red]")
        elif verbose and r.status == "passed":
            console.print(f"  [green]✓ {r.check}[/green]")

    if failed > 0:
        console.print("\n[red]Contract validation FAILED.[/red]")
        raise typer.Exit(1)
    console.print("\n[green]All contract checks PASSED.[/green]")


agency_app = typer.Typer(
    name="agency",
    help="Manage agency-agents lock and update workflow.",
    add_completion=False,
)
app.add_typer(agency_app, name="agency")


@agency_app.command("lock")
def agency_lock(
    ref: str = typer.Argument(..., help="Commit SHA or release tag to lock to"),
):
    """Lock agency-agents to a specific ref."""
    fleet_dir = _get_fleet_dir(Path.cwd())
    agency_path = fleet_dir / "agency.lock.yaml"

    if not agency_path.exists():
        console.print("[red]✗ agency.lock.yaml not found. Run 'hermes-fleet init' first.[/red]")
        raise typer.Exit(1)

    with open(agency_path) as f:
        data = yaml.safe_load(f) or {}
    data["ref"] = ref
    data["locked_at"] = datetime.now().strftime("%Y-%m-%d")
    with open(agency_path, "w") as f:
        yaml.dump(data, f, default_flow_style=False)
    console.print(f"[green]✓ agency.lock.yaml locked to {ref}[/green]")


DEFAULT_AGENCY_REPO = "https://github.com/niceai/agency-agents.git"


@agency_app.command("fetch")
def agency_fetch(
    repo: str = typer.Option(
        DEFAULT_AGENCY_REPO, "--repo", help="Agency-agents repository URL"
    ),
):
    """Fetch upstream agency-agents role definitions.

    Clones or pulls the upstream repo into .fleet/agency-agents-cache/.
    Does not modify fleet roles — use 'agency diff' and 'agency update'.
    """
    fleet_dir = _get_fleet_dir(Path.cwd())
    cache_dir = fleet_dir / "agency-agents-cache"
    agency_lock_path = fleet_dir / "agency.lock.yaml"

    if not fleet_dir.exists():
        console.print("[red]✗ No .fleet/ directory. Run 'hermes-fleet init' first.[/red]")
        raise typer.Exit(1)

    console.print(f"Fetching agency-agents from {repo}...")

    if cache_dir.exists():
        # Update existing cache
        import subprocess
        result = subprocess.run(
            ["git", "pull", "--ff-only"],
            cwd=cache_dir,
            capture_output=True, text=True
        )
        if result.returncode != 0:
            console.print(f"[red]✗ Failed to update cache: {result.stderr.strip()}[/red]")
            raise typer.Exit(1)
        console.print("[green]✓ Cache updated.[/green]")
    else:
        # Fresh clone
        import subprocess
        result = subprocess.run(
            ["git", "clone", "--depth", "1", repo, str(cache_dir)],
            capture_output=True, text=True
        )
        if result.returncode != 0:
            console.print(f"[red]✗ Failed to clone: {result.stderr.strip()}[/red]")
            raise typer.Exit(1)
        console.print(f"[green]✓ Cloned to {cache_dir}[/green]")

    # Get upstream HEAD
    import subprocess
    head = subprocess.run(
        ["git", "rev-parse", "HEAD"],
        cwd=cache_dir, capture_output=True, text=True
    ).stdout.strip()

    console.print(f"  Upstream HEAD: {head[:12]}")

    # Update lock file ref if not already set
    if agency_lock_path.exists():
        with open(agency_lock_path) as f:
            lock_data = yaml.safe_load(f) or {}
        if not lock_data.get("ref") or lock_data.get("ref") == "main":
            lock_data["ref"] = head[:12]
            lock_data["locked_at"] = datetime.now().strftime("%Y-%m-%d")
            with open(agency_lock_path, "w") as f:
                yaml.dump(lock_data, f, default_flow_style=False)
            console.print(f"  Lock updated to {head[:12]}")

    console.print("\nNext: hermes-fleet agency diff")


@agency_app.command("diff")
def agency_diff():
    """Show role definition changes since last locked ref."""
    fleet_dir = _get_fleet_dir(Path.cwd())
    cache_dir = fleet_dir / "agency-agents-cache"
    agency_lock_path = fleet_dir / "agency.lock.yaml"

    if not cache_dir.exists():
        console.print("[red]✗ No cache found. Run 'hermes-fleet agency fetch' first.[/red]")
        raise typer.Exit(1)

    if not agency_lock_path.exists():
        console.print("[red]✗ No agency.lock.yaml. Run 'hermes-fleet init' first.[/red]")
        raise typer.Exit(1)

    with open(agency_lock_path) as f:
        lock_data = yaml.safe_load(f) or {}
    locked_ref = lock_data.get("ref", "")

    if not locked_ref:
        console.print("[yellow]No ref locked. Showing current state only.[/yellow]")
        return

    import subprocess

    # Get current HEAD
    head = subprocess.run(
        ["git", "rev-parse", "HEAD"],
        cwd=cache_dir, capture_output=True, text=True
    ).stdout.strip()

    if head.startswith(locked_ref):
        console.print("[green]✓ Cache is at locked ref — no changes.[/green]")
        return

    # Show roles directory changes
    result = subprocess.run(
        ["git", "diff", "--stat", locked_ref, "HEAD", "--", "roles/"],
        cwd=cache_dir, capture_output=True, text=True
    )
    if result.stdout.strip():
        console.print("\n[bold]Role file changes:[/bold]")
        console.print(result.stdout)

    # Show detailed diff for role files
    diff_result = subprocess.run(
        ["git", "diff", locked_ref, "HEAD", "--", "roles/"],
        cwd=cache_dir, capture_output=True, text=True
    )
    if diff_result.stdout.strip():
        console.print("\n[bold]Detailed diff:[/bold]")
        for line in diff_result.stdout.split("\n"):
            if line.startswith("+") and not line.startswith("+++"):
                console.print(f"[green]{line}[/green]")
            elif line.startswith("-") and not line.startswith("---"):
                console.print(f"[red]{line}[/red]")
            else:
                console.print(line)
    else:
        console.print("[dim]No role changes detected.[/dim]")


@agency_app.command("update")
def agency_update(
    force: bool = typer.Option(
        False, "--force", help="Skip user approval prompt"
    ),
):
    """Compile upstream role definitions into fleet.

    Copies upstream role YAML files from .fleet/agency-agents-cache/roles/
    to .fleet/roles/, preserving metadata and adding provenance fields.
    """
    fleet_dir = _get_fleet_dir(Path.cwd())
    cache_dir = fleet_dir / "agency-agents-cache"
    roles_cache = cache_dir / "roles"

    if not roles_cache.exists() or not roles_cache.is_dir():
        console.print("[red]✗ No upstream roles found. Run 'hermes-fleet agency fetch' first.[/red]")
        raise typer.Exit(1)

    # Preview what will be imported
    upstream_roles = sorted(f.stem for f in roles_cache.glob("*.yaml"))
    if not upstream_roles:
        console.print("[yellow]No role YAML files found in upstream roles/.[/yellow]")
        return

    console.print(f"\n[bold]Upstream roles to import ({len(upstream_roles)}):[/bold]")
    for r in upstream_roles:
        console.print(f"  - {r}")

    if not force:
        console.print("\n[yellow]Review the diff first: hermes-fleet agency diff[/yellow]")
        console.print("[yellow]Run with --force to skip this prompt.[/yellow]")
        import typer as _typer
        if not _typer.confirm("\nProceed with update?"):
            console.print("[dim]Update cancelled.[/dim]")
            return

    # Import roles with provenance metadata
    custom_roles_dir = fleet_dir / "roles"
    custom_roles_dir.mkdir(parents=True, exist_ok=True)

    import subprocess
    head = subprocess.run(
        ["git", "rev-parse", "HEAD"],
        cwd=cache_dir, capture_output=True, text=True
    ).stdout.strip()

    repo_url = subprocess.run(
        ["git", "remote", "get-url", "origin"],
        cwd=cache_dir, capture_output=True, text=True
    ).stdout.strip()

    imported = 0
    for role_file in roles_cache.glob("*.yaml"):
        role_id = role_file.stem
        with open(role_file) as f:
            role_data = yaml.safe_load(f) or {}

        # Add provenance metadata
        role_data["source_repository"] = repo_url
        role_data["source_ref"] = head[:12]
        role_data["source_path"] = f"roles/{role_file.name}"
        role_data["source_hash"] = f"sha256:{head}"

        # Write to .fleet/roles/
        dst_path = custom_roles_dir / role_file.name
        with open(dst_path, "w") as f:
            yaml.dump(role_data, f, default_flow_style=False)
        imported += 1

    # Update lock
    agency_lock_path = fleet_dir / "agency.lock.yaml"
    lock_data = {}
    if agency_lock_path.exists():
        with open(agency_lock_path) as f:
            lock_data = yaml.safe_load(f) or {}
    lock_data["ref"] = head[:12]
    lock_data["locked_at"] = datetime.now().strftime("%Y-%m-%d")
    with open(agency_lock_path, "w") as f:
        yaml.dump(lock_data, f, default_flow_style=False)

    console.print(f"\n[green]✓ Imported {imported} upstream roles to .fleet/roles/[/green]")
    console.print(f"  Locked to {head[:12]}")
    console.print("\nNext: hermes-fleet validate")


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


# ──────────────────────────────────────────────
# Customize Command (v0.2+)
# ──────────────────────────────────────────────


customize_app = typer.Typer(
    name="customize",
    help="Customize fleet configuration (roles, permissions, resources).",
    add_completion=False,
)
app.add_typer(customize_app, name="customize")


@customize_app.command("status")
def customize_status():
    """Show current fleet configuration and available overrides."""
    fleet_dir = _get_fleet_dir(Path.cwd())
    if not fleet_dir.exists():
        console.print("[red]✗ No .fleet/ directory. Run 'hermes-fleet init' first.[/red]")
        raise typer.Exit(1)

    from hermes_fleet.teams import (
        list_available_roles,
        list_available_teams,
        list_available_permission_presets,
    )

    roles = list_available_roles(Path.cwd())
    teams = list_available_teams()
    presets = list_available_permission_presets(Path.cwd())

    fleet_yaml_path = fleet_dir / "fleet.yaml"
    fleet_config = {}
    if fleet_yaml_path.exists():
        with open(fleet_yaml_path) as f:
            fleet_config = yaml.safe_load(f) or {}

    console.print(f"\n[bold cyan]Fleet Configuration[/bold cyan]")
    console.print(f"  Team: {fleet_config.get('team', 'general-dev')}")
    console.print(f"  Fleet version: {fleet_config.get('fleet_version', '?')}")
    console.print(f"  Resources: {fleet_config.get('resources', {})}")

    custom_roles_dir = fleet_dir / "roles"
    custom_perms_dir = fleet_dir / "permissions"
    if custom_roles_dir.exists():
        custom_roles = [f.stem for f in custom_roles_dir.glob("*.yaml")]
        console.print(f"\n[green]Custom roles (in .fleet/roles/):[/green]")
        for r in custom_roles:
            console.print(f"  ✓ {r}")
    else:
        console.print(f"\n[dim]No custom roles (.fleet/roles/)[/dim]")

    if custom_perms_dir.exists():
        custom_perms = [f.stem for f in custom_perms_dir.glob("*.yaml")]
        console.print(f"\n[green]Custom permission presets (in .fleet/permissions/):[/green]")
        for p in custom_perms:
            console.print(f"  ✓ {p}")
    else:
        console.print(f"\n[dim]No custom permissions (.fleet/permissions/)[/dim]")

    console.print(f"\nAvailable teams ({len(teams)}): {', '.join(teams)}")
    console.print(f"Available roles ({len(roles)}): {', '.join(roles)}")
    console.print(f"Available permission presets ({len(presets)}): {', '.join(presets)}")
    console.print(f"\n[dim]To add custom roles:[/dim]")
    console.print(f"  mkdir -p .fleet/roles && cp <your-role.yaml> .fleet/roles/")
    console.print(f"\n[dim]To add custom permissions:[/dim]")
    console.print(f"  mkdir -p .fleet/permissions && cp <your-preset.yaml> .fleet/permissions/")
    console.print(f"\n[dim]To edit resources:[/dim]")
    console.print(f"  Edit .fleet/fleet.yaml -> add resources section")


@customize_app.command("roles")
def customize_roles(
    add: str = typer.Option(None, "--add", help="Path to a role YAML file to add as custom"),
):
    """Manage custom role definitions."""
    fleet_dir = _get_fleet_dir(Path.cwd())
    custom_dir = fleet_dir / "roles"

    if add:
        src_path = Path(add).resolve()
        if not src_path.exists():
            console.print(f"[red]✗ File not found: {src_path}[/red]")
            raise typer.Exit(1)
        custom_dir.mkdir(parents=True, exist_ok=True)
        role_id = src_path.stem
        dst_path = custom_dir / f"{role_id}.yaml"
        import shutil
        shutil.copy2(src_path, dst_path)
        console.print(f"[green]✓ Added custom role: {role_id}[/green]")
        console.print(f"  Source: {src_path}")
        console.print(f"  Dest: {dst_path}")
        return

    from hermes_fleet.teams import list_available_roles
    roles = list_available_roles(Path.cwd())
    custom_roles = []
    if custom_dir.exists():
        custom_roles = [f.stem for f in custom_dir.glob("*.yaml")]

    console.print(f"\n[bold]Available roles ({len(roles)}):[/bold]")
    for r in sorted(roles):
        marker = "[green]✓[/green]" if r in custom_roles else " "
        console.print(f"  {marker} {r}")

    console.print(f"\n[dim]Add a custom role:[/dim]")
    console.print(f"  hermes-fleet customize roles --add <path-to-role.yaml>")


@customize_app.command("permissions")
def customize_permissions(
    add: str = typer.Option(None, "--add", help="Path to a permission preset YAML to add"),
):
    """Manage custom permission presets."""
    fleet_dir = _get_fleet_dir(Path.cwd())
    custom_dir = fleet_dir / "permissions"

    if add:
        src_path = Path(add).resolve()
        if not src_path.exists():
            console.print(f"[red]✗ File not found: {src_path}[/red]")
            raise typer.Exit(1)
        custom_dir.mkdir(parents=True, exist_ok=True)
        preset_id = src_path.stem
        dst_path = custom_dir / f"{preset_id}.yaml"
        import shutil
        shutil.copy2(src_path, dst_path)
        console.print(f"[green]✓ Added custom permission preset: {preset_id}[/green]")
        return

    from hermes_fleet.teams import list_available_permission_presets
    presets = list_available_permission_presets(Path.cwd())
    console.print(f"\n[bold]Available permission presets ({len(presets)}):[/bold]")
    for p in presets:
        console.print(f"  - {p}")

    console.print(f"\n[dim]Add a custom preset:[/dim]")
    console.print(f"  hermes-fleet customize permissions --add <path-to-preset.yaml>")


@customize_app.command("resources")
def customize_resources(
    cpu: str = typer.Option(None, "--cpu", help="Default CPU limit (e.g. '0.5', '1.0')"),
    memory: str = typer.Option(None, "--memory", help="Default memory limit (e.g. '512M', '1G')"),
):
    """Edit default resource limits for fleet agents."""
    fleet_dir = _get_fleet_dir(Path.cwd())
    fleet_yaml_path = fleet_dir / "fleet.yaml"

    if not fleet_yaml_path.exists():
        console.print(f"[red]✗ No fleet.yaml. Run 'hermes-fleet init' first.[/red]")
        raise typer.Exit(1)

    with open(fleet_yaml_path) as f:
        config = yaml.safe_load(f) or {}

    resources = config.get("resources", {})
    changed = False
    if cpu:
        resources["default_cpu"] = cpu
        changed = True
    if memory:
        resources["default_memory"] = memory
        changed = True

    if not changed:
        console.print(f"[yellow]Current resources:[/yellow]")
        console.print(f"  CPU: {resources.get('default_cpu', '0.5')}")
        console.print(f"  Memory: {resources.get('default_memory', '512M')}")
        console.print(f"\n[dim]To change:[/dim]")
        console.print(f"  hermes-fleet customize resources --cpu 1.0 --memory 1G")
        return

    config["resources"] = resources
    with open(fleet_yaml_path, "w") as f:
        yaml.dump(config, f, default_flow_style=False)
    console.print(f"[green]✓ Resources updated:[/green]")
    console.print(f"  CPU: {resources.get('default_cpu', '0.5')}")
    console.print(f"  Memory: {resources.get('default_memory', '512M')}")


def main():
    """Entry point for the CLI."""
    app()


if __name__ == "__main__":
    main()
