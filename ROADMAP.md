# Hermes Agency — Roadmap

---

## v0.1 — Goal-to-Team Composition (Current)

**Goal**: Accept a goal → recommend team + roles + task DAG.
Output is informational (human-readable report + YAML spec).

### Features
- [ ] `plan <goal>` — keyword-heuristic team recommendation
- [ ] `init` — project scaffold with lock files
- [ ] SOUL.md generation per role (f-string from role presets)
- [ ] policy.yaml generation per role (f-string from permission presets)
- [ ] Task DAG output (YAML): ordered steps with input/output schemas
- [ ] Team presets: `general-dev`, `saas-medium`, `iphone-app`, `ai-app`, `security-audit`, `research-writing`, `content-creator`, `devops-deployment`
- [ ] Cross-reference validation (role → preset, team → role)
- [ ] Deterministic output (same goal → same team)

### Quality Bar
- All planning tests pass
- Generated SOUL.md + policy.yaml are valid
- DAG output is valid (no cycles, all deps resolvable)
- No Hermes global config is modified

---

## v0.2 — Kanban Integration

**Goal**: Plan output becomes executable Kanban tasks.

- [ ] `apply` — register plan with Hermes Kanban via `kanban_create`
- [ ] Skill injection: SOUL.md → Kanban task `skills` parameter
- [ ] Dependency graph → Kanban `parents` parameter
- [ ] Workspace kind per role → Kanban `workspace_kind`
- [ ] Max runtime per task type → Kanban `max_runtime_seconds`
- [ ] agency-agents upstream import (`agency fetch/diff/update`)
- [ ] Dual lock layers: `foundation.lock.yaml` + `agency.lock.yaml`
- [ ] Handoff contract I/O schema validation

---

## v0.3 — Multi-Goal and Repo Awareness

**Goal**: Handle existing repositories, multi-pipeline projects.

- [ ] `plan <goal> --repo <url>` — fingerprint existing repo, customize team
- [ ] Repo fingerprinting: language, deps, CI, risk flags
- [ ] Pipeline templates: save and reuse successful team compositions
- [ ] `plan --extend <existing-plan>` — add new tasks to existing DAG

---

## v0.4 — AI-Powered Planning

**Goal**: Foundation-bound planner uses LLM for team composition within locked constraints.

- [ ] Planner becomes AI-augmented (LLM constrained by `foundation.lock.yaml`)
- [ ] Determinism guarantee: same locks + same goal → same team
- [ ] Foundation update procedure (strict: proposal → impact → test → approve)
- [ ] Role-diff view for agency-agents updates

---

## v1.0 — Production

**Goal**: Stable, tested, documented planning-as-a-service.

- [ ] Full test suite with invariants (not change-detectors)
- [ ] CI/CD
- [ ] Documentation: every CLI command, every preset, every contract
- [ ] Integration test: plan → apply → Kanban executes → verify result
- [ ] Non-goal enforcement: reviewer never writes code, orchestrator never implements
