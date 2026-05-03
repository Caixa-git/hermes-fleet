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

## v0.3 — Container Lifecycle Management (Superseded)

**Note**: v0.3 and v0.4 are superseded by v0.5 (Solitude Runtime).
The old long-running-container model (N+1 containers, concurrent, networked) is replaced
by a sequential 1-shot container pipeline. See `docs/design/v0.5-solitude-runtime.md`.

### What was built
- [x] `hermes-fleet up/down/status/logs/restart` — container lifecycle CLI
- [x] Volume persistence management
- [x] Per-agent network isolation
- [x] Hermetic pipeline test

### Why superseded
The solitude model (zero containers at rest, one container at a time, file-only handoff)
provides stronger isolation with less complexity. Container lifecycle → obsolete.
Volume management → obsolete. Network isolation → obsolete.

---

## v0.4 — Isolation Runtime (Superseded)

See v0.3 note. v0.4 runtime isolation (memory/communication/network layers) is replaced
by solitude (no coexistence → no isolation machinery needed).

### What was built
- [x] Memory isolation (per-agent volumes, volume lifecycle)
- [x] Communication isolation (gateway routing, port lockdown)
- [x] Network isolation (4-mode policy, temp access infrastructure)
- [x] Agent lifecycle state machine (CREATED → ARCHIVED)
- [x] Handoff contract runtime validation
- [x] Token budget per session
- [x] Dedicated test suite (83 tests)

### Why superseded
v0.3 + v0.4 solved a problem that no longer exists. If agents never coexist,
there is nothing to isolate. Network policy, port publishing, volume ACLs,
gateway routing — all unnecessary in the solitude model.

---

## v0.5 — Solitude Runtime (Current)

**Goal**: Sequential pipeline of 1-shot `docker run --rm` agents.
Zero containers at rest. One agent at a time. Complete solitude.
File-only handoff orchestrated by a deterministic scheduler.

**Philosophy**: Not isolation (coexistence with barriers) but solitude
(non-existence). An agent runs, finishes, vanishes. The next agent
has no evidence the previous one existed.

**Design doc**: `docs/design/v0.5-solitude-runtime.md`

### Pipeline Engine (Kanban-inspired)
- [ ] Scheduler: sequential execution of pipeline steps
- [ ] Task runner: `docker run --rm` abstraction with env/policy injection
- [ ] Step state machine: PENDING → RUNNING → DONE / FAILED / BLOCKED
- [ ] Retry with backoff (configurable per step)
- [ ] Blocked state: pause pipeline, notify user, resume later
- [ ] Execution log per step under `.fleet/runs/<id>/`

### Handoff Contract as I/O Schema
- [ ] HandoffContract rewritten: source_output → transform → target_input
- [ ] `validate_handoff_doc()` → pipeline input/output validation
- [ ] Automated handoff data transformation by scheduler
- [ ] No `from_roles` / `allowed_next_roles` (orchestrator-only communication)

### Specialized Agent Injection (agency-agents)
- [ ] Per-step SOUL.md injection (role identity from upstream)
- [ ] Per-step policy.yaml injection (task types, filesystem, commands)
- [ ] Per-step handoff contract injection (I/O expectations)
- [ ] Provenance metadata preserved in execution logs

### Team Composition
- [ ] Planner evolves: keyword match → pipeline generation
- [ ] Team presets include `pipeline` field (execution order)
- [ ] Dependency analysis: from-scratch vs existing-repo ordering
- [ ] User-approvable pipeline plan before execution

### CLI
- [ ] `hermes-fleet plan "<goal>"` — generate pipeline with contracts
- [ ] `hermes-fleet run` — execute pipeline
- [ ] `hermes-fleet status` — show pipeline progress
- [ ] `hermes-fleet logs <step>` — per-step logs
- [ ] `hermes-fleet resume` — continue from blocked step

### Testing
- [ ] Scheduler unit tests (mocked docker)
- [ ] Task runner unit tests
- [ ] Pipeline integration test (end-to-end with actual docker)
- [ ] Handoff contract I/O schema tests

---

## v0.6 — Recovery and Observability

**Goal**: Handle failures gracefully. Surface pipeline state clearly.

- [ ] Per-step timeout with SIGKILL escalation (from Kanban: max_runtime)
- [ ] Workspace retention policy (auto-clean old runs)
- [ ] Post-mortem report: which steps failed, why, how to retry
- [ ] Rich status output: execution timeline per step
- [ ] `hermes-fleet retry --step <id>` — retry a failed step

---

## v0.7 — Multi-Pipeline and Repo Ingestion

**Goal**: Run multiple pipelines. Ingest existing repositories.

- [ ] `hermes-fleet fleet new "<goal>"` — create new project from goal
- [ ] `hermes-fleet fleet ingest <repo-url> "<goal>"` — analyze existing repo
- [ ] Repo fingerprinting for pipeline customization
- [ ] Parallel pipeline execution (experimental — limited by solitude model)
- [ ] Pipeline templates: save and reuse successful pipelines
