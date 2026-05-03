# Hermes Fleet — Research Notes

> Research conducted prior to implementing v0.1.
> Date: 2026-05-03

---

## 1. Hermes Agent Documentation

### Source: Codebase at `/workspace/hermes-agent/`

**Key findings relevant to hermes-fleet:**

#### Docker Environment (`tools/environments/docker.py`)
- Hermes already has a hardened Docker execution backend.
- Default security args: `--cap-drop ALL`, `--cap-add DAC_OVERRIDE CHOWN FOWNER`, `--security-opt no-new-privileges`, `--pids-limit 256`, tmpfs mounts for `/tmp`, `/var/tmp`, `/run`.
- Supports both root (with gosu cap-add SETUID/SETGID) and non-root user modes.
- Forward env vars via `docker_forward_env` allowlist.
- The container itself is the security boundary.
- **Takeaway**: hermes-fleet should generate Docker Compose config that aligns with these patterns, but doesn't need to reimplement them.

#### Delegation / Subagents
- Hermes has `delegate_task` which spawns subagents in isolated contexts.
- Subagents get their own conversation, terminal session, and toolset.
- Only final summary is returned.
- **Takeaway**: hermes-fleet should generate Kanban-based handoff contracts that mirror the delegation pattern but at the container level.

#### Profiles (`hermes_constants.py`)
- Profile-aware paths via `get_hermes_home()`.
- Config at `~/.hermes/config.yaml`, API keys at `~/.hermes/.env`.
- **Takeaway**: hermes-fleet containers must NOT mount or read these paths.

#### Kanban Spec
- There is a `docs/hermes-kanban-v1-spec.pdf` in the repo.
- **Takeaway**: hermes-fleet should generate Kanban handoff templates compatible with this spec.

#### Security
- Command approval flow, DM pairing, container isolation documented.
- Security is a first-class concern.
- **Takeaway**: hermes-fleet's safe defaults must match or exceed Hermes' own security posture.

### What hermes-fleet should NOT duplicate
- Actual Docker container management (Hermes already has this).
- Agent conversation loop (Hermes AIAgent class).
- Tool discovery / toolset management.
- Memory persistence.
- Cron scheduling.

### What hermes-fleet ADDS
- Team presets (e.g., "SaaS Product Team" with 9 agents).
- Role definition → SOUL.md + policy.yaml generation.
- Machine-readable policy for runtime enforcement.
- Docker Compose generation with per-agent isolation.
- Kanban handoff contract generation.
- Safe-defaults validator.
- Compilation of role definitions into enforceable runtime boundaries.

---

## 2. awesome-hermes-agent

### Source: GitHub API

- Repo `NousResearch/awesome-hermes-agent` does NOT exist at this time.
- No official curated awesome list for Hermes Agent ecosystem found publicly.
- Several community projects exist: hermesclaw (WeChat bridge) mentioned in README.
- **Takeaway**: hermes-fleet could be the first structured ecosystem extension project.

---

## 3. agency-agents

### Source: GitHub — `agency-agents/agency-agents`

- A Python multi-agent framework by the community.
- Roles defined as Python classes inheriting from `Role` base class.
- Also supports YAML persona files with keys: `name`, `description`, `system_prompt`, `tools` (list), `llm_config` (dict).
- Only 3 example personas shipped: `assistant`, `researcher`, `weather_bot`.
- Framework is minimal and generic — not specific to Hermes.
- Has a `load_persona()` function to load YAML → Role instance.

### How hermes-fleet can use agency-agents later
- Create an importer interface that reads agency-agents YAML persona files.
- Compile the persona's `system_prompt` into a SOUL.md.
- Map `tools` into policy.yaml allowed commands.
- Map `llm_config` into agent configuration.
- For v0.1: do NOT hard-depend on agency-agents. Use a small internal role library.

---

## 4. Existing Multi-Agent Projects (Landscape)

| Project | Strengths | Gaps for our use case |
|---------|-----------|----------------------|
| **AutoGen** (Microsoft) | Conversational agent teams, handoff | No Docker isolation, agents share environment |
| **CrewAI** | Role-based teams, tool assignment | No sandboxing, all agents in same process |
| **LangGraph** | Graph-based DAG orchestration | No agent lifecycle or isolation |
| **OpenAI Swarm** | Handoff primitives | Experimental, not production-ready |
| **MetaGPT** | Simulated software teams | Domain-specific, no security isolation |
| **CAMEL** | Role-playing interactions | Research-focused, no production support |
| **Docker Agent Runtime** | Per-agent Docker containers | No orchestration or handoff |
| **E2B** | Cloud sandbox for code exec | Cloud-only, no multi-agent orchestration |

### Unique Value of hermes-fleet
hermes-fleet is the **only open-source project** that combines:
- Multi-agent team orchestration
- Per-agent Docker container isolation (not just process-level)
- Machine-readable policy enforcement (policy.yaml)
- Role-based identity (SOUL.md)
- Kanban handoff contract layer
- Least-privilege defaults

---

## 5. Design Decisions for v0.1

### Docker Compose Security Template
Reference the Hermes Agent pattern but as Docker Compose:

```yaml
services:
  <agent-id>:
    image: nousresearch/hermes-agent:latest
    cap_drop:
      - ALL
    cap_add:
      - DAC_OVERRIDE  # bind mount writes
      - CHOWN
      - FOWNER
    security_opt:
      - no-new-privileges:true
    pids_limit: 256
    tmpfs:
      - /tmp:rw,noexec,nosuid,size=512m  # note: Hermes uses exec, but fleet uses stricter defaults
      - /run:rw,noexec,nosuid,size=64m
    read_only: true  # Hermes doesn't default to this, but fleet should
    volumes:
      - <agent-id>_data:/opt/data
      - <workspace>/<agent-worktree>:/workspace/<agent-worktree>
    environment:
      - HERMES_PROFILE=<agent-id>
    networks:
      - <network-policy>
    deploy:
      resources:
        limits:
          cpus: '0.5'
          memory: 512M
```

### Permission Presets
The brief defines several presets. For v0.1, implement in code as Python data structures:

- `orchestrator_safe` — kanban_only workspace, no app code writes
- `repo_readonly` — read-only workspace, no network
- `docs_rw_repo_ro` — docs writeable, repo read-only
- `frontend_worktree_rw` — own worktree, no backend/infra access
- `backend_worktree_rw` — own worktree, no frontend/infra access
- `readonly_no_network` — strictly read-only
- `test_runner` — read-only repo, test tmp, no network

### Filesystem Structure
- All output goes to `.fleet/` in the project root.
- Never touches `~/.hermes` or any global Hermes state.

### CLI Surface for v0.1
- `hermes-fleet init` — create `.fleet/fleet.yaml`
- `hermes-fleet plan "<goal>"` — recommend a team
- `hermes-fleet generate` — generate all config
- `hermes-fleet test safe-defaults` — validate generated config

---

## 6. Technical Stack

Confirmed from brief:
- **Python** 3.11+
- **Typer** — CLI framework
- **Pydantic** — schema validation
- **PyYAML** — YAML I/O
- **Jinja2** — template rendering
- **pytest** — testing

No database. No web UI. No Docker dependency for testing.

---

## 7. agency-agents Import Strategy (Future)

```python
# Placeholder interface for v0.1:
class AgencyAgentsImporter:
    """Read agency-agents YAML persona files and convert to hermes-fleet roles."""
    
    def load(self, path: str) -> RoleDefinition:
        """Parse agency-agents persona YAML → hermes-fleet RoleDefinition."""
        ...
    
    def to_soul(self, role: RoleDefinition) -> str:
        """Generate SOUL.md from agency-agents persona."""
        ...

    def to_policy(self, role: RoleDefinition) -> dict:
        """Generate policy.yaml from agency-agents persona."""
        ...
```

---

## 8. Key Risks and Mitigations

| Risk | Mitigation |
|------|-----------|
| v0.1 scope creep | Strict adherence to brief's v0.1 boundary checklist |
| Accidental Hermes dependency | No Hermes imports, no ~/.hermes access, self-contained |
| Template drift from actual Hermes behavior | Generate conservative safe defaults; document assumptions |
| Over-engineering | Prefer flat data structures over deep class hierarchies; no database |
