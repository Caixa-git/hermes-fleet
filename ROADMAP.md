# Hermes Fleet — Roadmap

---

## v0.1 — Generator and Validator

**Goal**: Self-contained CLI that generates secure, isolated Hermes Agent team configurations.
**Isolation facet**: Role (team presets, SOUL.md), Boundary (policy.yaml, Docker Compose, safe-defaults)

### Features
- [x] Team presets: `general-dev`, `saas-medium`
- [x] Role definitions for all agents in presets
- [x] Permission presets (repo_readonly, frontend_worktree_rw, etc.)
- [x] CLI: `hermes-fleet init` — create `.fleet/fleet.yaml`
- [x] CLI: `hermes-fleet plan "<goal>"` — recommend team via keyword heuristic
- [x] CLI: `hermes-fleet generate` — generate all config
- [x] CLI: `hermes-fleet test safe-defaults` — validate output
- [x] SOUL.md generation (Python f-strings)
- [x] policy.yaml generation (Python f-strings + yaml.dump)
- [x] Docker Compose generation (per-agent services with security defaults)
- [x] Kanban handoff template generation
- [x] Safe-defaults validator (22 checks across 16 check functions)
- [x] Automated test suite (161 tests)

### Quality Bar
- All tests pass
- Generated files are deterministic
- v0.1 scope is respected
- No real secrets are generated
- No global Hermes config is modified
- No existing Hermes state is read or written
- Docker Compose is generated but not run
- Security defaults are conservative

---

## v0.2 — Team Expansion, Role Fidelity, and agency-agents Import

**Goal**: More team presets, user customization, agency-agents import, and role-fidelity infrastructure.
**Isolation facet**: Role (agency-agents import, provenance metadata, preserve compiler), Completion (contract schemas, handoff contracts)

### Role Fidelity
- [x] agency-agents upstream import interface: fetch, parse, compile agency-agents YAML persona files into fleet roles
- [x] SOUL.md provenance metadata: `source_repository`, `source_ref`, `source_path`, `source_hash`
- [x] Preserve-mode compiler: original role specs included verbatim or near-verbatim with provenance fields
- [x] Role-diff view: show what changed when agency-agents ref is updated (`hermes-fleet agency diff`)

### Two Lock Layers
- **foundation.lock.yaml** (in `.fleet/`): pins four design foundation sources (see `DESIGN_FOUNDATIONS.md`). Updated via strict proposal → impact analysis → regression test → human approval → version bump.
- **agency.lock.yaml** (in `.fleet/`): pins upstream role inventory. Updated via lighter fetch → diff → compile → preserve test → policy impact check → handoff impact check → user approval → promote.
- The two layers are independent. Foundation updates are rare (months to years). Agency updates are frequent (weeks to months).
- The onboarding AI is a foundation-bound planner: it synthesizes teams within the locked boundaries. It does not improvise beyond the locks.

### agency-agents Update Model
- [x] Locked ref mechanism: commit SHA or release tag stored in `.fleet/agency.lock.yaml`
- [x] `hermes-fleet agency fetch` — pull latest upstream without applying
- [x] `hermes-fleet agency diff` — show role definition changes since locked ref
- [x] `hermes-fleet agency update` — compile + provenance metadata → custom roles → user approval → promote
- [x] Never auto-apply latest `main` (always requires explicit `agency update`)

### Team Expansion
- [x] Additional team presets: `iphone-app`, `ai-app`, `security-audit`, `research-writing`, `content-creator`, `devops-deployment` (8 total)
- [x] `hermes-fleet customize` — fleet configuration (roles, permissions, resources)
- [x] Custom role definitions from local YAML files (`.fleet/roles/`)
- [x] Permission preset customization (`.fleet/permissions/`)
- [x] Expanded safe-defaults checks (CPU/memory limits, task types)
- [x] Per-agent CPU/memory resource customization (fleet.yaml → Docker Compose)

### Contract-Driven Team Composition
- [x] **Team Proposal schema**: onboarders (human or AI) output constrained to a fixed schema — `recommended_team_id`, `rationale`, optional `customizations` only
- [x] **Team Contract**: Pydantic schema for team YAML files with id, name, agents, optional_agents
- [x] **Role Contract**: Pydantic schema with provenance, permission_preset, handoff_contract, task types
- [x] **Handoff Contract**: Pydantic schema with from_roles, allowed_next_roles, required_fields, validation_rules — 4 YAML presets deployed
- [x] **foundation.lock.yaml / agency.lock.yaml**: dual lock layers with Pydantic contracts
- [x] **Cross-reference validation**: team→role, role→preset, role→handoff, handoff→role all verified
- [x] **Deterministic allocation**: same locks + same goal → same team every time

### Testing (v0.2+)
- [x] **Contract Schema Tests**: every contract validates against its Pydantic schema
- [x] **Cross-Reference Tests**: all role/handoff/preset references resolve
- [x] **Safety Invariant Tests**: hard rules that must never be violated (reviewers read-only, etc.)
- [x] **Deterministic Allocation Tests**: same input → identical output (8 teams, Docker Compose, resources)
- [x] **Handoff Validation Tests**: handoffs enforce their own required fields

---

## v0.3 — Container Lifecycle Management (Current)

**Goal**: Actually run the generated containers with full isolation — memory, filesystem, network.
**Isolation facet**: Boundary (container lifecycle, volume persistence, network isolation)

### Container Lifecycle
- [x] `hermes-fleet up` — start the fleet (docker compose up)
- [x] `hermes-fleet down` — stop the fleet
- [x] `hermes-fleet status` — check agent health (container-level: running/stopped/crashed)
- [x] `hermes-fleet logs <agent>` — view agent logs
- [x] `hermes-fleet restart <agent>` — restart individual agent
- [x] Container health checks and restart policies
- [x] Volume persistence management
- [x] Per-agent network: sub-agents default to `network: none`, orchestrator has network access

### Validation
- [x] `hermes-fleet validate` extended with handoff contract required_fields check:
  every handoff contract must define at least one required_field

---

## v0.4 — Isolation Runtime

**Goal**: Three-layer isolation enforcement at runtime — memory, communication, and network.
**Isolation facet**: All facets — the runtime makes isolation real.

### Memory Isolation
- Per-agent memory volumes: agent A cannot read agent B's memory
- Memory persistence across restarts (volume lifecycle)
- Memory wipe on agent retirement

### Communication Isolation
- Gateway routing: user messages go to orchestrator only
- Sub-agents cannot send messages outside their container
- All agent-to-any communication proxied through orchestrator
- No direct agent-to-agent messaging

### Network Isolation
- Role-based network policy: `isolated` / `outbound-only` / `proxy`
- Default for sub-agents: `network: none`
- Orchestrator sets network policy at team composition time
- Temporary network access requests: agent → orchestrator → user approval → time-limited grant → auto-revoke

### Agent Runtime
- Agent lifecycle state machine: CREATED → ACTIVE → IDLE → COMPLETED → ARCHIVED
- IDLE agents reject messages; orchestrator must wake them explicitly
- Token budget per session (`max_iterations_per_session`)

### Handoff Contract Runtime
- Handoff contract validation at handoff time (required fields, role checks)
- Handoff rejection with orchestrator notification
- `from_roles` and `allowed_next_roles` enforcement

---

## v0.5 — Orchestrator Integration

**Goal**: The orchestrator becomes the sole communication channel. All fleet interaction passes through it.
**Isolation facet**: Orchestrator — the entity that can cross isolation boundaries.

- **Orchestrator as sole intermediary**: no direct agent-to-agent, no agent-to-user
- **Task assignment**: orchestrator assigns tasks to sub-agents based on role and capacity
- **Completion flow**: agent completes task → reports to orchestrator → orchestrator verifies and aggregates
- **User approval gate**: orchestrator presents aggregated results → user approves or redirects
- **Direction adjustment**: user rejects or redirects → orchestrator reassigns with updated instructions
- **Orchestrator SOUL.md** with fleet management capabilities: assign, monitor, verify, report
- **Stalled agent detection** — agents exceeding budget or producing no output
- **Network exception handling**: sub-agent requests temp access → orchestrator asks user → time-limited grant
- **Terminal-based orchestrator dashboard** — real-time view of agent states, tasks, pending approvals

### Interaction Model

```
Agent ──task complete──→ Orchestrator (verify + aggregate)
                           Orchestrator ──report──→ User
                           User ──approve or redirect──→ Orchestrator
                           Orchestrator ──next task or reassign──→ Agent
```

- Orchestrator has full autonomy over sub-agent task assignment and monitoring
- User interaction is limited to: reviewing completed work, approving results, giving direction
- No per-agent approval gates. The orchestrator is the single point of user contact
- Policy violations are handled by policy.yaml enforcement, not by user approval

---

## v0.6 — Policy Enforcement and Recovery

**Goal**: Runtime enforcement of isolation policies. Violation detection, escalation, and recovery.
**Isolation facet**: Boundary — the walls are enforced, not just declared.

### Policy Enforcement
- Policy enforcer sidecar per container
- Filesystem write allow/deny enforcement
- Command execution allow/deny enforcement
- Network access enforcement (allowlist-based)
- Secret injection with allowlist enforcement
- Violation detection and logging
- Soft/medium/hard/critical violation levels
- Isolation drift detection and alerting

### Runtime Handoff Validation
- Role-specific handoff validation against required outputs
- Isolation audit: periodic verification that agent A cannot access agent B's data

### Recovery and Self-Healing
- Soft violations: request correction, document in audit log
- Medium violations: block task, notify orchestrator
- Hard violations: pause container, preserve workspace snapshot, require review
- Critical violations: kill container, redact output, create security incident
- Workspace snapshot preservation for forensic analysis

---

## v0.7 — Kanban Runtime and Fleet Mode

**Goal**: Task visualization and fleet lifecycle management. Repo ingestion for existing projects.
**Isolation facet**: Completion — structured, visible, auditable work flow.

### Kanban Runtime
- `hermes-fleet task create` — create a task
- `hermes-fleet task assign <agent>` — assign task to agent
- `hermes-fleet task handoff <from> <to>` — handoff with validation
- `hermes-fleet task complete <id>` — complete task with gates
- Task contract validation (required inputs/outputs)
- Blocker reporting and escalation
- Kanban board visualization (terminal-based web UI)

### Fleet Mode (New Project)
- `hermes-fleet fleet new "<goal>"` — create new fleeted repo from goal
- Team proposal from goal only
- Auto-create fleeted repo on GitHub

### Fleet Mode (Existing Repo)
- `hermes-fleet fleet ingest <repo-url> "<goal>"` — ingest existing repo
- Read-only source clone, fleeted repo creation
- Repository fingerprint generation
- Team proposal from fingerprint + goal
- First issue auto-created for orchestrator

---

## v1.0 — Production-Ready

- CI/CD integration (GitHub Actions, automated releases)
- Published to PyPI
- Comprehensive documentation
- Web dashboard (fleet overview, agent logs, Kanban board)
- Secret management integration (no placeholders)
- Audit log export
- Multiple parallel active fleets
- Helm chart for Kubernetes deployment
- Agency-agents lifecycle management: full update workflow
- Role-fidelity certification: guaranteed provenance chain

---

## Future Ideas

- **Self-healing agents**: detect violations and recover automatically
- **Dynamic scaling**: add/remove agents mid-project
- **Fleet templates**: save and share team configurations
- **Marketplace**: community role definitions
- **Hermes-native mode**: integrate directly with Hermes Agent gateway
- **Multi-project orchestration**: coordinate across multiple repositories
- **AI onboarding provider**: LLM-backed team recommendation (removed from v0.4 scope)
