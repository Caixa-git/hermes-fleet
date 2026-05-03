# Hermes Fleet — Technical Specification v0.5

---

## 1. Overview

Hermes Fleet is a self-contained CLI tool that generates secure, role-based Hermes Agent team configurations and manages their container lifecycle. v0.3 extends the generator into a **fleet runner** — it can start, stop, monitor, and restart agent containers via Docker. It does not require any existing Hermes installation.

---

## 2. The Pillar: Isolation

Hermes Fleet is built on one non-negotiable principle: **every agent is isolated**.

No agent can see another agent's memory, files, network, or secrets. No agent can talk to another agent directly. Even the user cannot talk to sub-agents directly. Every message, every piece of data, every network request must pass through **the orchestrator** — the sole entity that holds all the keys.

From this single pillar, four facets emerge.

### 2.1 Role — Who lives in each room

*Key question: "Who is this agent, and what should it do?"*

**Role Fidelity** — agency-agents is the upstream role specification dependency.
The compiler's default mode is **preserve** — original role specifications
are included in SOUL.md verbatim or near-verbatim, never arbitrarily
summarized by AI.

Every SOUL.md records provenance metadata:
- `source_repository` — URL of the agency-agents repository
- `source_ref` — locked commit SHA or release tag
- `source_path` — path within the repository
- `source_hash` — content hash of the original specification

This ensures traceability from upstream role definition to fleet agent identity.

**Role artifacts**: SOUL.md, agency-agents lock, provenance metadata,
identity drift self-checks.

### 2.2 Boundary — The walls of the room

*Key question: "What can this agent do, and what is off-limits?"*

**Isolation** — Role identity declared in SOUL.md is aspirational. The actual
boundary is enforced by policy.yaml and Docker.

- Every agent gets separate filesystem, memory, network, secret, and command permissions.
- Permission boundaries are expressed in **policy.yaml** — machine-readable and testable.
- The runtime boundary is the **container**, not the prompt.
- Isolation must be verifiable through automated checks.
- Sub-agents default to `network: none`. Orchestrator sets policy at composition time.
- Temporary network exceptions: agent → orchestrator → user approval → time-limited grant → auto-revoke.

**Boundary artifacts**: policy.yaml, Docker Compose, safe-defaults validator,
permission presets.

### 2.3 Completion — How work passes between rooms

*Key question: "Is the work really done, and can the next person pick it up?"*

**Handoff + Verification** — Handoff between agents is a **role-specific contract**, not a generic message.

- Each role defines its own handoff requirements (required outputs, format, validation gates).
- The handoff must be self-contained: the receiving agent can start work from it without reading the sending agent's full history.
- Common templates provide a baseline, but each role extends them with role-specific fields.
- Completion gates validate that the handoff contract is fulfilled before the task moves to the next agent.

Done = output + verification + record + handoff.

**Completion artifacts**: Handoff contracts, completion gates, kanban templates,
handoff validation rules.

### 2.4 Orchestrator — The only one who opens doors

The orchestrator is not a separate pillar. It is the runtime agent that can cross isolation boundaries — the sole communication channel between any two entities in the fleet.

- It assigns tasks to sub-agents. They execute in isolation.
- It receives completed work. Verifies. Aggregates.
- It reports to the user. The user approves or redirects.
- It reassigns. The cycle continues.
- If a sub-agent needs temporary network access, it requests the orchestrator. The orchestrator asks the user. User grants a time-limited exception. Isolation is restored automatically on expiry.

Interaction model:

```
Agent ──task complete──→ Orchestrator (verify + aggregate)
                           Orchestrator ──report──→ User
                           User ──approve or redirect──→ Orchestrator
                           Orchestrator ──next task or reassign──→ Agent
```

- Sub-agents never contact the user directly. The orchestrator is the sole intermediary.
- No per-agent approval gates. No approval thresholds.
- Policy violations are handled by policy.yaml enforcement, not by user approval.

> **Implemented in v0.3**: Container lifecycle commands (up/down/status/logs/restart)
> and handoff contract required_fields validation.

---

## 3. CLI Commands

### 3.1 `hermes-fleet init`

Creates local project configuration.

```
Usage: hermes-fleet init [OPTIONS]

Options:
  --dir TEXT  Project directory (default: current working directory)
  --help      Show this message and exit.
```

Creates:
- `.fleet/fleet.yaml` — default project configuration

The `fleet.yaml` template:

```yaml
# Hermes Fleet project configuration
fleet_version: 0.1.0
name: unnamed-fleet
team: general-dev  # default team
output_dir: .fleet/generated
```

### 3.2 `hermes-fleet plan <goal>`

Analyzes a goal and recommends a team.

```
Usage: hermes-fleet plan [OPTIONS] GOAL

Arguments:
  GOAL  Description of the work to be done

Options:
  --show-details  Show full agent roster and permissions
  --help          Show this message and exit.
```

Returns:
- Recommended team name
- List of agents in the team
- Brief rationale

**Keyword heuristics** (v0.1 only):

- **"saas", "subscription", "dashboard", "auth", "billing", "payment", "web app", "platform", "api", "crm"** → saas-medium
- **"ios", "iphone", "apple", "swift", "mobile app", "native app"** → iphone-app
- **"ai", "machine learning", "llm", "rag", "chatbot", "gpt", "neural"** → ai-app
- **"security audit", "penetration test", "vulnerability", "compliance"** → security-audit
- **"research", "whitepaper", "literature review", "study", "report"** → research-writing
- **"content", "blog", "marketing", "social media", "seo"** → content-creator
- **"devops", "ci/cd", "deployment", "infrastructure", "terraform", "kubernetes"** → devops-deployment
- **Everything else** → general-dev

### 3.3 `hermes-fleet generate`

Generates all agent configuration files.

```
Usage: hermes-fleet generate [OPTIONS]

Options:
  --team TEXT     Override team selection
  --force         Overwrite existing generated files
  --help          Show this message and exit.
```

Generates:
- `.fleet/generated/docker-compose.generated.yaml`
- `.fleet/generated/agents/<agent-id>/SOUL.md`
- `.fleet/generated/agents/<agent-id>/policy.yaml`
- `.fleet/generated/kanban/task-template.md`
- `.fleet/generated/kanban/handoff-template.md`
- `.fleet/generated/kanban/completion-gates.yaml`

Cross-reference validation during generation:
- All agents in the team must have corresponding role definitions
- All role `permission_preset` fields must resolve to known preset files

### 3.4 `hermes-fleet validate`

Validates all preset contracts and cross-references without generating output.

```
Usage: hermes-fleet validate [OPTIONS]

Options:
  --verbose, -v  Show all checks including passing
  --help         Show this message and exit.
```

Loads all teams, roles, handoff contracts, and permission presets, then runs:
- All team agents have corresponding role contracts
- All role permission_presets resolve to known presets
- All handoff contracts have at least one required_field (v0.3)
- Handoff contract role references resolve to existing roles
- Role handoff_contract references resolve to existing contracts

Returns exit code 0 if all checks pass, 1 if any check fails.

### 3.5 `hermes-fleet test safe-defaults`

Validates generated configuration against safe-default rules.

```
Usage: hermes-fleet test safe-defaults [OPTIONS]

Options:
  --generated-dir PATH  Path to generated output (default: .fleet/generated)
  --verbose             Show all checks, including passing
  --help                Show this message and exit.
```

Returns exit code 0 if all checks pass, 1 if any check fails.

### 3.6 `hermes-fleet up`

Starts the fleet containers.

```
Usage: hermes-fleet up [OPTIONS]

Options:
  --detach / --attach  Run in background (default: detach)
  --help               Show this message and exit.
```

Runs `docker compose up` with the generated compose file. Requires Docker.

### 3.7 `hermes-fleet down`

Stops the fleet containers.

```
Usage: hermes-fleet down [OPTIONS]

Options:
  --volumes, -v  Remove named volumes
  --help         Show this message and exit.
```

### 3.8 `hermes-fleet status`

Checks fleet container status.

```
Usage: hermes-fleet status [OPTIONS]

Options:
  --help  Show this message and exit.
```

Shows per-container state (running/exited), health, and uptime.

### 3.9 `hermes-fleet logs <agent>`

Shows logs for a specific agent container.

```
Usage: hermes-fleet logs [OPTIONS] AGENT

Arguments:
  AGENT  Agent/service ID (e.g. 'orchestrator', 'reviewer')

Options:
  --tail, -t INTEGER  Number of lines from the end (default: 100)
  --help              Show this message and exit.
```

### 3.10 `hermes-fleet restart <agent>`

Restarts a specific agent container.

```
Usage: hermes-fleet restart [OPTIONS] AGENT

Arguments:
  AGENT  Agent/service ID to restart (e.g. 'orchestrator')

Options:
  --help  Show this message and exit.
```

### 3.11 `hermes-fleet customize`

Manages custom roles, permissions, and resources.

```
Usage: hermes-fleet customize [OPTIONS] COMMAND [ARGS]...

Commands:
  roles        Add or list custom role definitions
  permissions  Add or list custom permission presets
  resources    Edit default CPU/memory limits
```

### 3.12 `hermes-fleet agency`

Manages agency-agents import and update workflow.

```
Usage: hermes-fleet agency [OPTIONS] COMMAND [ARGS]...

Commands:
  lock    Lock agency-agents to a specific ref
  fetch   Pull latest upstream without applying
  diff    Show role definition changes since locked ref
  update  Compile + provenance metadata → promote
```

---

## 4. Team Presets

### 4.1 General Development Team (`general-dev`)

**Purpose**: Small, general-purpose development team for ordinary software tasks.

**Agents**:
- `orchestrator` — Task management, handoffs; no application code writes
- `fullstack-developer` — Implementation; own worktree; no deployment
- `reviewer` — Code review; read-only repo access
- `qa-tester` — Test execution; report failures; no silent fixes
- `technical-writer` — Documentation; read-only repo

### 4.2 Medium SaaS Team (`saas-medium`)

**Purpose**: Balanced team for a medium-sized SaaS MVP.

**Agents**:
- `orchestrator` — Kanban management only
- `product-manager` — Docs read/write; repo read-only
- `ux-designer` — Design docs read/write; repo read-only
- `frontend-developer` — Frontend worktree; no production secrets
- `backend-developer` — Backend worktree; dev secrets only
- `database-architect` — Schema worktree; destructive migrations require approval
- `qa-tester` — Read-only repo; test execution
- `security-reviewer` — Read-only repo; no network; no secrets; security reports only
- `technical-writer` — Docs read/write; repo read-only

**Optional (disabled by default)**:
- `deployer` — Deployment; requires explicit approval
- `growth-marketer` — Future
- `customer-support-specialist` — Future

### 4.3 iOS/iPhone App Team (`iphone-app`)

**Purpose**: Native iOS application development with Swift.

**Agents**: `orchestrator`, `frontend-developer`, `reviewer`, `qa-tester`

### 4.4 AI/ML App Team (`ai-app`)

**Purpose**: LLM-powered applications, RAG systems, and ML model integration.

**Agents**: `orchestrator`, `frontend-developer`, `backend-developer`, `reviewer`, `qa-tester`, `technical-writer`

### 4.5 Security Audit Team (`security-audit`)

**Purpose**: Code security review, penetration testing methodology, vulnerability assessment.

**Agents**: `orchestrator`, `security-reviewer`, `reviewer`

### 4.6 Research and Writing Team (`research-writing`)

**Purpose**: Technical research papers, literature reviews, whitepapers.

**Agents**: `orchestrator`, `technical-writer`, `reviewer`

### 4.7 Content Creator Team (`content-creator`)

**Purpose**: Blog posts, marketing content, social media, SEO strategy.

**Agents**: `orchestrator`, `technical-writer`, `reviewer`

### 4.8 DevOps Deployment Team (`devops-deployment`)

**Purpose**: CI/CD pipelines, infrastructure as code, Kubernetes deployment.

**Agents**: `orchestrator`, `deployer`, `reviewer`

---

## 5. Role Definitions

Each role has:

- **id**: Unique role identifier (e.g., `orchestrator`)
- **name**: Human-readable name (e.g., "Orchestrator")
- **description**: One-line role description
- **mission**: What the agent is responsible for
- **non_goals**: What the agent must not do
- **permission_preset**: References a preset file in `presets/permissions/` that defines filesystem, network, and secret access. See section 6.
- **allowed_tasks**: Task types this agent may accept
- **forbidden_tasks**: Task types this agent must refuse
- **allowed_commands**: Shell commands this agent may execute
- **denied_commands**: Shell commands this agent must not execute
- **handoff** (dict): Completeness contract — what the agent must produce when handing off work
  - `required_outputs`: List of output types required before handoff
- **completion_gates** (dict): Conditions that must be met before marking complete
  - `required`: List of gate names that must pass
- **allowed_workspaces**, **allowed_paths**, **readonly_paths**, **forbidden_paths**, **network_access**, **secret_allowlist**: These fields are defined in the referenced `permission_preset`, not inline in the role.

### Role File Format (YAML)

```yaml
id: security-reviewer
name: Security Reviewer
description: Reviews code and configuration for security vulnerabilities.
mission: >
  Identify security issues, assess risk severity, and recommend fixes.
  Do not modify code. Do not access secrets. Report findings only.
non_goals: |
  - Implementation or feature development
  - Deployment or infrastructure changes
  - Product scope decisions
  - Access to secrets or production credentials

permission_preset: readonly_no_network

allowed_tasks:
  - security_review
  - risk_analysis
  - dependency_review
  - vulnerability_assessment

forbidden_tasks:
  - implementation
  - deployment
  - product_scope_decision
  - code_modification

allowed_commands:
  - grep
  - rg
  - npm audit
  - pip audit

denied_commands:
  - git push
  - npm install
  - docker
  - ssh
  - terraform apply

handoff_required_outputs:
  - risk_summary
  - severity_labels
  - recommended_fixes
  - approval_or_block

completion_gates:
  required:
    - explicit_approve_or_block
    - no_code_modification
```

---

## 6. Permission Presets

- **`orchestrator_safe`** — workspace: kanban_only, repo_write: false, secrets: [], network: control_plane_only
- **`repo_readonly`** — workspace: readonly, repo_write: false, secrets: [], network: none
- **`docs_rw_repo_ro`** — workspace: docs_write, repo_write: false, secrets: [], network: none
- **`frontend_worktree_rw`** — workspace: own_worktree_rw, repo_write: true, secrets: PUBLIC_ONLY, network: package_registry
- **`backend_worktree_rw`** — workspace: own_worktree_rw, repo_write: true, secrets: DEV_ONLY, network: package_registry
- **`schema_worktree_rw`** — workspace: own_worktree_rw, repo_write: true, secrets: DATABASE_URL_DEV, network: package_registry
- **`readonly_no_network`** — workspace: readonly, repo_write: false, secrets: [], network: none
- **`test_runner`** — workspace: readonly_or_test_tmp, repo_write: false, secrets: [], network: none

---

## 7. Docker Compose Generation

### 7.1 Service Template

```yaml
services:
  <agent-id>:
    image: nousresearch/hermes-agent:latest  # placeholder; user provides
    container_name: hermes-fleet-<agent-id>-<project-hash>
    cap_drop:
      - ALL
    cap_add:
      - DAC_OVERRIDE
      - CHOWN
      - FOWNER
    security_opt:
      - no-new-privileges:true
    pids_limit: 256
    read_only: true
    tmpfs:
      - /tmp:rw,noexec,nosuid,size=512m
      - /run:rw,noexec,nosuid,size=64m
    volumes:
      - <agent-id>_data:/opt/data
      - type: bind
        source: ./<agent-worktree>
        target: /workspace/<agent-worktree>
        read_only: <true/false>
    environment:
      - HERMES_PROFILE=<agent-id>
    networks:
      - <network-name>
    deploy:
      resources:
        limits:
          cpus: '0.5'
          memory: 512M
```

### 7.2 Non-Negotiable Defaults (must be true unless user overrides)

- **No privileged containers** — `privileged: true` must NOT exist in any service
- **No docker.sock mount** — `/var/run/docker.sock` must NOT be mounted
- **No host network mode** — `network_mode: host` must NOT exist
- **`cap_drop: [ALL]`** — Every service must have this
- **`no-new-privileges: true`** — Every service must have this
- **`pids_limit` set** — Every service must have a pid limit (default 256)
- **Separate volumes per agent** — Each agent must have its own named volume for /opt/data
- **Read-only root filesystem** — `read_only: true` must be set on all services
- **No shared global .env** — Environment variables must be per-service, not `env_file: .env`
- **Resource limits set** — CPU and memory limits should be present
- **Healthcheck configured** — Every service has a healthcheck (pgrep) with 30s interval
- **Restart policy set** — Every service is set to `restart: unless-stopped`

### 7.3 Network Configuration

Generated networks:

```
networks:
  fleet-control-plane:
    internal: true  # orchestrator communication
  fleet-no-net: {}  # isolated (internal: true by default in compose)
```

Agent network assignment:
- Default: `fleet-no-net` (no external access)
- Agents needing package registry: `fleet-control-plane` + appropriate egress
- Or later: user-configured network access

---

## 8. SOUL.md Format (Generated from Template)

Each SOUL.md includes these sections:

```markdown
# Identity
<!-- Who this agent is -->

# Mission
<!-- What this agent is responsible for -->

# Non-Goals
<!-- What this agent must not do -->

# Allowed Work
<!-- What kinds of tasks this agent may accept -->

# Forbidden Work
<!-- What kinds of tasks this agent must refuse -->

# Kanban Behavior
<!-- How the agent receives tasks and completes work -->

# Handoff Contract
<!-- What the agent must include when handing off -->

# Output Format
<!-- Required output structure -->

# Failure Behavior
<!-- What to do when blocked or missing permissions -->

# Identity Drift Self-Check
<!-- Pre-work and post-work role checklists -->
```

---

## 9. Safe-Defaults Validator Checks

### 9.1 Team Tests
- [ ] general-dev team can be loaded
- [ ] saas-medium team can be loaded

### 9.2 Generation Tests
- [ ] SOUL.md is generated for every agent in the team
- [ ] policy.yaml is generated for every agent in the team
- [ ] Docker Compose service is generated for every agent

### 9.3 Docker Security Tests
- [ ] Every agent has a separate /opt/data volume
- [ ] No service has `privileged: true`
- [ ] No service mounts `/var/run/docker.sock`
- [ ] Every service has `cap_drop: ["ALL"]`
- [ ] Every service has `no-new-privileges: true`
- [ ] Every service has `pids_limit` set
- [ ] Every service has `read_only: true` set
- [ ] No service uses `network_mode: host`

### 9.4 Policy Tests
- [ ] Reviewer workspace is read-only
- [ ] Security-reviewer has `network_access: none`
- [ ] Orchestrator has `kanban_only` workspace
- [ ] Deployer is disabled by default
- [ ] No production secret is injected

### 9.5 Kanban Tests
- [ ] Kanban task template is generated
- [ ] Kanban handoff template is generated
- [ ] Completion gates template is generated

### 9.6 Isolation Tests
- [ ] No generated output writes to `~/.hermes`
- [ ] No generated output depends on an existing Hermes profile
- [ ] No generated output contains real secret values

---

## 10. Package Structure

```
hermes-fleet/
├── README.md
├── ARCHITECTURE.md
├── ROADMAP.md
├── SPEC.md
├── pyproject.toml
├── src/
│   └── hermes_fleet/
│       ├── __init__.py
│       ├── checks.py
│       ├── cli.py
│       ├── contracts.py
│       ├── docker_compose.py
│       ├── generator.py
│       ├── kanban.py
│       ├── planner.py
│       ├── policy.py
│       ├── runner.py
│       ├── safe_defaults.py
│       └── teams.py
├── presets/
│   ├── permissions/
│   │   ├── backend_worktree_rw.yaml
│   │   ├── docs_rw_repo_ro.yaml
│   │   ├── frontend_worktree_rw.yaml
│   │   ├── orchestrator_safe.yaml
│   │   ├── readonly_no_network.yaml
│   │   ├── repo_readonly.yaml
│   │   ├── schema_worktree_rw.yaml
│   │   └── test_runner.yaml
│   ├── teams/
│   │   ├── general-dev.yaml
│   │   └── saas-medium.yaml
│   └── roles/
│       ├── orchestrator.yaml
│       ├── fullstack-developer.yaml
│       ├── reviewer.yaml
│       ├── qa-tester.yaml
│       ├── technical-writer.yaml
│       ├── product-manager.yaml
│       ├── ux-designer.yaml
│       ├── frontend-developer.yaml
│       ├── backend-developer.yaml
│       ├── database-architect.yaml
│       ├── security-reviewer.yaml
│       ├── deployer.yaml
│       ├── growth-marketer.yaml
│       └── customer-support-specialist.yaml
├── tests/
│   ├── test_checks.py
│   ├── test_cli_generate.py
│   ├── test_contract_schemas.py
│   ├── test_deterministic_allocation.py
│   ├── test_docker_compose_generation.py
│   ├── test_end_to_end.py
│   ├── test_kanban_templates.py
│   ├── test_planner.py
│   ├── test_policy.py
│   ├── test_policy_generation.py
│   ├── test_safe_defaults.py
│   ├── test_soul_generation.py
│   └── test_team_presets.py

---

## 11. Technical Stack

- **Language**: Python 3.10+ — Hermes Agent is Python; easy integration later
- **CLI Framework**: Typer — Fast CLI development, auto --help
- **Schema Validation**: Pydantic — Type-safe data models, serialization
- **YAML**: PyYAML — Read/write YAML presets and generated config
- **Templates**: Python f-strings — Inline rendering in generator.py and kanban.py
- **Testing**: pytest + pyyaml — Standard Python testing
- **Testing Strategy**: Unit + snapshot + structural — Verify content, structure, and safety

---

## 12. Output Determinism

All generated output must be deterministic for the same input:

- No timestamps in generated files
- No random UUIDs or hashes unless required for uniqueness
- Stable ordering of agents in lists
- Stable ordering of policy fields
- Stable YAML serialization (consistent key order)

> **Note**: `foundation.lock.yaml` and `agency.lock.yaml` (for pinning foundation
> sources and upstream role versions) are v0.2+ scope. In v0.1, determinism is
> achieved through static preset files and sorted rendering alone.

This ensures:
- Version control diffs are meaningful
- Tests are reproducible
- Generated config can be compared across runs

---

## 13. Non-Goals for v0.1

- Running Docker containers
- Executing Hermes agents
- Reading or writing ~/.hermes
- Importing existing Hermes profiles
- Accessing real API keys or secrets
- Building a web or terminal UI
- Using a database
- Full Kanban application
- Real-time agent monitoring
- Self-healing or recovery
- Production secret management
- Deployment pipeline integration

---

## 14. Future Scope

Designs beyond v0.1 are maintained as separate documents:

- **`docs/design/REPO_FLEET_MODE.md`** — GitHub integration, fleet mode for existing repos (v0.5+)

The following v0.2 designs are now implemented in v0.1/v0.2:
- Two lock layers (`foundation.lock.yaml`, `agency.lock.yaml`) — created by `init`, managed via `agency` commands
- Agency-agents import protocol (`agency fetch/diff/update` commands)
- TeamContract, RoleContract, PermissionPresetContract, HandoffContract — all in `src/hermes_fleet/contracts.py`
- Cross-reference validation in `validate` command
- Handoff YAML presets in `presets/handoffs/`
- Role → handoff contract references in all 14 role YAMLs
