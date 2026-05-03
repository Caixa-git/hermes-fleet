# Hermes Fleet — Technical Specification v0.1

---

## 1. Overview

Hermes Fleet is a self-contained CLI tool that generates secure, role-based Hermes Agent team configurations. v0.1 is a **generator and validator** only — it does not execute agents, manage containers, or require any existing Hermes installation.

---

## 2. Core Pillars

Hermes Fleet is defined by three non-negotiable pillars that govern all design decisions. These pillars are themselves grounded in four design foundation sources, documented in `DESIGN_FOUNDATIONS.md`. The foundations are locked via `foundation.lock.yaml` and updated through a strict proposal → impact analysis → regression test → human approval → version bump process.

### 2.1 Role Fidelity

**agency-agents** is the upstream role specification dependency. The compiler's default mode is **preserve** — original role specifications are included in SOUL.md verbatim or near-verbatim, never arbitrarily summarized by AI.

Every SOUL.md records provenance metadata:
- `source_repository` — URL of the agency-agents repository
- `source_ref` — locked commit SHA or release tag
- `source_path` — path within the repository
- `source_hash` — content hash of the original specification

This ensures traceability from upstream role definition to fleet agent identity.

### 2.2 Isolation

Role identity declared in SOUL.md is aspirational. The actual boundary is enforced by policy.yaml and Docker.

- Every agent gets separate filesystem, memory, network, secret, and command permissions.
- Permission boundaries are expressed in **policy.yaml** — machine-readable and testable.
- The runtime boundary is the **container**, not the prompt.
- Isolation must be verifiable through automated checks.

### 2.3 Handoff

Handoff between agents is a **role-specific contract**, not a generic message.

- Each role defines its own handoff requirements (required outputs, format, validation gates).
- The handoff must be self-contained: the receiving agent can start work from it without reading the sending agent's full history.
- Common templates provide a baseline, but each role extends them with role-specific fields.
- Completion gates validate that the handoff contract is fulfilled before the task moves to the next agent.

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

| Keywords | Team |
|----------|------|
| "saas", "subscription", "dashboard", "auth", "billing", "payment", "web app", "platform" | saas-medium |
| Everything else | general-dev |

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

### 3.4 `hermes-fleet test safe-defaults`

Validates generated configuration against safe-default rules.

```
Usage: hermes-fleet test safe-defaults [OPTIONS]

Options:
  --generated-dir PATH  Path to generated output (default: .fleet/generated)
  --verbose             Show all checks, including passing
  --help                Show this message and exit.
```

Returns exit code 0 if all checks pass, 1 if any check fails.

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

---

## 5. Role Definitions

Each role has:

- **id**: Unique role identifier (e.g., `orchestrator`)
- **name**: Human-readable name (e.g., "Orchestrator")
- **description**: One-line role description
- **mission**: What the agent is responsible for
- **non_goals**: What the agent must not do
- **allowed_tasks**: Task types this agent may accept
- **forbidden_tasks**: Task types this agent must refuse
- **allowed_workspaces**: Workspace access patterns (full, own_worktree, readonly, none)
- **allowed_paths**: Glob patterns of writable paths
- **readonly_paths**: Glob patterns of read-only paths
- **forbidden_paths**: Glob patterns of inaccessible paths
- **network_access**: Network policy (none, web_readonly, package_registry, internal, deploy_only)
- **secret_allowlist**: Environment variable names this agent may access
- **allowed_commands**: Shell commands this agent may execute
- **denied_commands**: Shell commands this agent must not execute
- **handoff_required_outputs**: Fields required when handing off work
- **completion_gates**: Conditions that must be met before marking complete

### Role File Format (YAML)

```yaml
id: security-reviewer
name: Security Reviewer
description: Reviews code and configuration for security vulnerabilities
mission: >
  Identify security issues, assess risk, and recommend fixes.
  Do not modify code.
non_goals: |
  - Implementation or feature development
  - Deployment or infrastructure changes
  - Product scope decisions

allowed_tasks:
  - security_review
  - risk_analysis
  - dependency_review

forbidden_tasks:
  - implementation
  - deployment
  - product_scope_decision

allowed_workspaces: readonly
readonly_paths:
  - repo/**

forbidden_paths:
  - .env
  - secrets/**
  - other-agents/**

network_access: none

secret_allowlist: []

allowed_commands:
  - grep
  - rg
  - npm audit
  - pip audit
  - pytest

denied_commands:
  - git push
  - npm publish
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

| Preset ID | Workspace | Repo Write | Secrets | Network |
|-----------|-----------|-----------|---------|---------|
| `orchestrator_safe` | kanban_only | false | [] | control_plane_only |
| `repo_readonly` | readonly | false | [] | none |
| `docs_rw_repo_ro` | docs_write | false | [] | none |
| `frontend_worktree_rw` | own_worktree_rw | true | PUBLIC_ONLY | package_registry |
| `backend_worktree_rw` | own_worktree_rw | true | DEV_ONLY | package_registry |
| `readonly_no_network` | readonly | false | [] | none |
| `test_runner` | readonly_or_test_tmp | false | [] | none |

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

| Rule | Enforcement |
|------|------------|
| No privileged containers | `privileged: true` must NOT exist in any service |
| No docker.sock mount | `/var/run/docker.sock` must NOT be mounted |
| No host network mode | `network_mode: host` must NOT exist |
| `cap_drop: [ALL]` | Every service must have this |
| `no-new-privileges: true` | Every service must have this |
| `pids_limit` set | Every service must have a pid limit (default 256) |
| Separate volumes per agent | Each agent must have its own named volume for /opt/data |
| Read-only root filesystem | `read_only: true` must be set on all services |
| No shared global .env | Environment variables must be per-service, not `env_file: .env` |
| Resource limits set | CPU and memory limits should be present |

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
├── RESEARCH_NOTES.md
├── pyproject.toml
├── src/
│   └── hermes_fleet/
│       ├── __init__.py
│       ├── cli.py
│       ├── planner.py
│       ├── teams.py
│       ├── roles.py
│       ├── schema.py
│       ├── generator.py
│       ├── policy.py
│       ├── docker_compose.py
│       ├── kanban.py
│       └── safe_defaults.py
├── presets/
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
│       └── security-reviewer.yaml
├── tests/
│   ├── __init__.py
│   ├── test_team_presets.py
│   ├── test_soul_generation.py
│   ├── test_policy_generation.py
│   ├── test_docker_compose_generation.py
│   ├── test_safe_defaults.py
│   └── test_kanban_templates.py
└── examples/
    ├── general-dev/
    └── saas-medium/
```

---

## 11. Technical Stack

| Component | Choice | Reason |
|-----------|--------|--------|
| Language | Python 3.10+ | Hermes Agent is Python; easy integration later |
| CLI Framework | Typer | Fast CLI development, auto --help |
| Schema Validation | Pydantic | Type-safe data models, serialization |
| YAML | PyYAML | Read/write YAML presets and generated config |
| Templates | Python f-strings | Inline rendering in generator.py and kanban.py |
| Testing | pytest + pyyaml | Standard Python testing |
| Testing Strategy | Unit + snapshot + structural | Verify content, structure, and safety |

---

## 12. Output Determinism

All generated output must be deterministic for the same input, given the
same locked foundation and agency refs:

- `foundation.lock.yaml` pins the design foundation sources
- `agency.lock.yaml` pins the upstream role specification versions

- No timestamps in generated files
- No random UUIDs or hashes unless required for uniqueness
- Stable ordering of agents in lists
- Stable ordering of policy fields
- Stable YAML serialization (consistent key order)

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

## 14. Agency-Agents Update Model

### 14.1 Two Lock Layers

Hermes Fleet maintains two independent lock layers:

| Lock File | Purpose | Update Cadence | Process |
|-----------|---------|----------------|---------|
| `foundation.lock.yaml` | Pins design foundation sources (see `DESIGN_FOUNDATIONS.md`) | Months to years | Strict proposal → impact analysis → regression test → human approval → version bump |
| `agency.lock.yaml` | Pins upstream role inventory from agency-agents | Weeks to months | Lighter fetch → diff → compile → preserve test → policy impact check → handoff impact check → user approval → promote |

The onboarding AI is a **foundation-bound planner**: it synthesizes teams
within the boundaries of both lock layers. It does not improvise new
principles, role taxonomies, or handoff protocols beyond what the locks
allow. New research or new principles are recorded as proposals only and
never auto-applied.

### 14.2 Update Process

Updating from the upstream `agency-agents` repository follows a controlled, auditable process:

```
1. Fetch     git fetch upstream main
2. Diff      Show changed role definitions since locked ref
3. Compile   Run fleet compiler against new specs
4. Preserve test     Verify existing role integrity is preserved
5. Policy impact check       Detect any permission changes
6. Handoff impact check      Detect any handoff requirement changes
7. User approval     Present diff summary; require explicit confirmation
8. Promote   Update locked ref; regenerate affected agents
```

### 14.3 Locking

- The framework **never auto-applies** `main`. Always lock to a specific commit SHA or release tag.
- The locked ref is stored in the project's `fleet.yaml` or a dedicated `.fleet/agency-agents.lock` file.
- The locked ref is validated before any compile operation.

### 14.4 New Role Adoption Gate

New roles from upstream are only adopted after they pass all three pillar checks:

| Pillar | Gate |
|--------|------|
| Role Fidelity | Provenance metadata is complete (`source_repository`, `source_ref`, `source_path`, `source_hash`) |
| Isolation | policy.yaml filesystem, network, secret, and command boundaries are defined |
| Handoff | Role-specific handoff requirements exist (not just common template fallback) |

If any gate fails, the compiler blocks promotion and reports the specific deficiency.

### 14.5 CLI Interface (Future)

```text
hermes-fleet agency fetch       # Pull latest upstream (no apply)
hermes-fleet agency diff         # Show role changes since locked ref
hermes-fleet agency update       # Full update workflow with gates
hermes-fleet agency lock <ref>   # Pin to specific commit/tag
```

---

## 15. Contract Schemas (v0.2+)

### 15.1 Overview

Teams, roles, and handoffs are expressed as formal, testable contracts. These schemas replace ad-hoc YAML presets with typed, cross-referenced data structures. An AI or human onboarding agent cannot freely invent team structures — its output is constrained to a `Team Proposal` schema that references known contracts.

### 15.2 Team Contract

```yaml
team_contract:
  id: str                          # unique identifier
  required_capabilities: [str]     # what the team must be able to do
  role_inventory: [str]            # ordered list of role IDs
  permission_preset_mapping:       # role_id → preset_id
    role_id: preset_id
  handoff_contract_inventory:      # list of handoff contract IDs
    - contract_id
```

Validation rules:
- `id` must be unique across all team contracts
- Every entry in `role_inventory` must have a corresponding `permission_preset_mapping`
- Every `permission_preset_mapping` value must reference a known permission preset
- Every entry in `handoff_contract_inventory` must reference a known Handoff Contract
- All `required_capabilities` must be covered by at least one role

### 15.3 Role Contract

```yaml
role_contract:
  id: str
  source:
    repository: str                 # URL of upstream repo
    ref: str                        # commit SHA or release tag
    path: str                       # path to spec within repo
    hash: str                       # content hash of original spec
  role_fidelity_mode: preserve | near_verbatim | summarize
  allowed_task_types: [str]
  forbidden_task_types: [str]
  permission_preset: str            # reference to permission preset
  handoff_contract: str             # reference to handoff contract
  identity_drift_guards:
    pre_work: [str]
    post_work: [str]
```

Validation rules:
- `role_fidelity_mode` must be one of the three enumerated values
- `preserve` mode requires that `source.hash` matches the hash of the up-to-date fetched spec
- `allowed_task_types` and `forbidden_task_types` must not overlap
- `permission_preset` must reference a known permission preset
- `handoff_contract` must reference a known Handoff Contract

### 15.4 Handoff Contract

```yaml
handoff_contract:
  id: str
  from_roles: [str]                 # which roles may originate this handoff
  allowed_next_roles: [str]         # which roles may receive this handoff
  required_fields: [str]            # fields that must be present in the handoff document
  validation_rules:
    - field: str
      required: bool
      min_length: int               # (optional)
      max_length: int               # (optional)
      enum: [str]                   # (optional) if set, value must be in this list
      min_items: int                # (optional) if field is a list
      regex: str                    # (optional) pattern to match
  completion_gate:
    required: [str]
```

Validation rules:
- Every entry in `from_roles` and `allowed_next_roles` must reference a known role contract
- `from_roles` and `allowed_next_roles` must not overlap (no self-handoffs without explicit intent)
- `required_fields` must be a subset of fields that have a `required: true` validation rule
- `validation_rules` must not conflict (e.g., `enum` and `regex` on the same field)
- `completion_gate.required` lists the conditions checked after handoff delivery

### 15.5 Team Proposal Schema

When the Planner or an AI onboarding agent creates a team, its output schema:

```yaml
team_proposal:
  goal: str
  recommended_team_id: str          # must match a known Team Contract
  rationale: str
  customizations:
    agents: [str]                   # optional subset of role_inventory
    permission_overrides:           # optional role_id → preset_id
      role_id: preset_id
    handoff_overrides:              # optional contract_id → new contract_id
      contract_id: new_contract_id
```

Proposal is rejected if:
- `recommended_team_id` does not match a known Team Contract
- Any role in `customizations.agents` is not in the Team Contract's `role_inventory`
- Any `permission_overrides` references an unknown preset
- Any `handoff_overrides` references an unknown contract

### 15.6 Test Categories

All tests use mocked inputs. No real AI API calls, Docker execution, or Hermes agent execution.

| Category | Scope |
|----------|-------|
| Contract Schema Tests | Each contract validates against its Pydantic schema |
| Cross-Reference Tests | All role/handoff/preset references between contracts resolve |
| Safety Invariant Tests | Hard rules that can never be violated under any valid configuration |
| Deterministic Allocation Tests | Same input → identical output across multiple runs |
| Handoff Validation Tests | Handoff contracts enforce their validation rules at runtime |

---

## 16. Repo Fleet Mode (v0.5+)

See `REPO_FLEET_MODE.md` for the complete design. This section
summarizes the SPEC-relevant aspects.

### 16.1 New Data Types

**Repository Fingerprint** — stored in `.fleet/fingerprint.yaml`:

| Field | Type | Source |
|-------|------|--------|
| `fingerprint.source_repository` | string (URL) | User-provided repo URL |
| `fingerprint.source_ref` | string | Default: "main" |
| `fingerprint.language.primary` | string | Detected from repo contents |
| `fingerprint.complexity.lines_of_code` | integer | Counted from repo |
| `fingerprint.security_posture.has_security_policy` | boolean | File detection |
| `fingerprint.risk_flags` | list of strings | Pattern matching |

**Merge Gate Config** — stored in `.fleet/merge-gate.yaml`:

| Field | Type | Default |
|-------|------|---------|
| `auto_merge.low_risk` | boolean | true |
| `auto_merge.low_risk.require_ci` | boolean | true |
| `auto_merge.medium_risk` | boolean | true |
| `auto_merge.medium_risk.require_review` | boolean | true |
| `human_approval.high_risk` | boolean | true (always blocks) |
| `never_auto_merge_patterns` | list of strings | `[".env", "*secret*", "deploy/*", ".github/workflows/*"]` |

### 16.2 Fleet Mode CLI (Future)

```text
hermes-fleet fleet new "<goal>"                  # New Project Mode
hermes-fleet fleet ingest <repo-url> "<goal>"    # Existing Repo Mode
hermes-fleet fleet status                        # Show fleet state
hermes-fleet fleet fingerprint                   # Regenerate fingerprint
```

### 16.3 GitHub API Integration

Fleet Mode requires a GitHub token with these scopes:

| Scope | Required For |
|-------|-------------|
| `repo` | Create fleeted repo, push branches, create PRs |
| `issues:write` | Create issues in fleeted repo |
| `pull_requests:write` | Create and review PRs |

The token is stored in `.fleet/github-token` (never in `.env` or
in any generated file). It is used only by the Fleet Orchestrator agent.

### 16.4 Safety Invariants

- Source repo is never modified (read-only clone)
- Fleeted repo starts with empty secrets and no deployment config
- Main branch direct push is forbidden (branch protection enforced)
- High-risk changes always require human approval
- `.env` and secret-like files are never auto-merged
- All agent actions are audited via GitHub Issues and PRs

---

## 17. Community Signals Schema (v0.5+)

See `REPO_FLEET_MODE.md` section 10 for the full design.

### 17.1 Deterministic Parameters

| Parameter | Type | Default | Description |
|-----------|------|---------|-------------|
| `time_window_days` | integer | 90 | Analyze issues/PRs from the last N days |
| `min_reaction_threshold` | integer | 5 | Minimum 👍 reactions for "high community interest" |
| `stale_issue_days` | integer | 365 | No activity in N days = stale |
| `recurring_issue_min_duplicates` | integer | 3 | Threshold for "recurring problem" |
| `label_priority_order` | list of strings | `["bug", "security", "enhancement", "documentation", "question"]` | Priority for label-based task selection |

### 17.2 Signal Data Types

```yaml
community_signals:
  analyzed_at: timestamp
  time_window_days: integer
  issues:
    total_open: integer
    labeled_bug: integer
    labeled_security: integer
    high_reaction_count: integer
    recurring_patterns:
      - description: string
        duplicate_count: integer
  prs:
    total_open: integer
    abandoned_count: integer
  maintainer_signals:
    pinned_issues: [string]
    recent_release_notes: [string]
```

---

## 18. Exit Strategy Schema (v0.5+)

See `REPO_FLEET_MODE.md` section 11 for the full design.

### 18.1 Exit Criteria

```yaml
# .fleet/exit-strategy.yaml
exit_strategy:
  max_pr_count: integer        # default: 50
  max_duration_days: integer   # default: 90
  inactivity_timeout_days: integer  # default: 30

  must_have: [string]
  should_have: [string]
  stop_when: [string]
  human_approval_needed: [string]
```

### 18.2 Exit Trigger Types

| Trigger | Type | Description |
|---------|------|-------------|
| Goal completion | automatic | All must-have items resolved |
| PR budget exhausted | automatic | `pr_count >= max_pr_count` |
| No low-risk tasks remain | heuristic | Only high-risk items left |
| Human decision required | escalation | Architecture, secrets, deployment |
| Source repo diverged | automatic | Fingerprint ref is stale |

### 18.3 Exit Report

See `REPO_FLEET_MODE.md` section 12 for the `FLEETED_EXIT_REPORT.md`
template. The report is generated automatically when any exit trigger
fires.
