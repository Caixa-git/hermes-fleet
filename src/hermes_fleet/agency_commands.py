"""Agency-agents lock and update workflow commands.

Extracted from cli.py for maintainability. Self-contained helper.
"""
from __future__ import annotations

from datetime import datetime
from pathlib import Path

import typer
import yaml
from rich.console import Console

console = Console()


def _get_fleet_dir(project_dir: Path) -> Path:
    return project_dir / ".fleet"


DEFAULT_AGENCY_REPO = "https://github.com/niceai/agency-agents.git"

agency_app = typer.Typer(
    name="agency",
    help="Manage agency-agents lock and update workflow.",
    add_completion=False,
)


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
    import subprocess

    fleet_dir = _get_fleet_dir(Path.cwd())
    cache_dir = fleet_dir / "agency-agents-cache"
    agency_lock_path = fleet_dir / "agency.lock.yaml"

    if not fleet_dir.exists():
        console.print("[red]✗ No .fleet/ directory. Run 'hermes-fleet init' first.[/red]")
        raise typer.Exit(1)

    console.print(f"Fetching agency-agents from {repo}...")

    if cache_dir.exists():
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
        result = subprocess.run(
            ["git", "clone", "--depth", "1", repo, str(cache_dir)],
            capture_output=True, text=True
        )
        if result.returncode != 0:
            console.print(f"[red]✗ Failed to clone: {result.stderr.strip()}[/red]")
            raise typer.Exit(1)
        console.print(f"[green]✓ Cloned to {cache_dir}[/green]")

    head = subprocess.run(
        ["git", "rev-parse", "HEAD"],
        cwd=cache_dir, capture_output=True, text=True
    ).stdout.strip()

    console.print(f"  Upstream HEAD: {head[:12]}")

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
    import subprocess

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

    head = subprocess.run(
        ["git", "rev-parse", "HEAD"],
        cwd=cache_dir, capture_output=True, text=True
    ).stdout.strip()

    if head.startswith(locked_ref):
        console.print("[green]✓ Cache is at locked ref — no changes.[/green]")
        return

    result = subprocess.run(
        ["git", "diff", "--stat", locked_ref, "HEAD", "--", "roles/"],
        cwd=cache_dir, capture_output=True, text=True
    )
    if result.stdout.strip():
        console.print("\n[bold]Role file changes:[/bold]")
        console.print(result.stdout)

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
    import subprocess

    fleet_dir = _get_fleet_dir(Path.cwd())
    cache_dir = fleet_dir / "agency-agents-cache"
    roles_cache = cache_dir / "roles"

    if not roles_cache.exists() or not roles_cache.is_dir():
        console.print("[red]✗ No upstream roles found. Run 'hermes-fleet agency fetch' first.[/red]")
        raise typer.Exit(1)

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
        if not typer.confirm("\nProceed with update?"):
            console.print("[dim]Update cancelled.[/dim]")
            return

    custom_roles_dir = fleet_dir / "roles"
    custom_roles_dir.mkdir(parents=True, exist_ok=True)

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

        role_data["source_repository"] = repo_url
        role_data["source_ref"] = head[:12]
        role_data["source_path"] = f"roles/{role_file.name}"
        role_data["source_hash"] = f"sha256:{head}"

        dst_path = custom_roles_dir / role_file.name
        with open(dst_path, "w") as f:
            yaml.dump(role_data, f, default_flow_style=False)
        imported += 1

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
