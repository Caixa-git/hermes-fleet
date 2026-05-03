# Hermes Fleet — Repo Fleet Mode

> **Status**: Design document (not yet implemented). Targeted for v0.5+.
>
> This document describes how Hermes Fleet ingests an existing repository
> and creates an isolated "fleeted" workspace where an agent team can
> autonomously improve the codebase through PR-based collaboration.

---

## 1. Three Modes

Hermes Fleet supports three starting modes, depending on whether the
user has a repository and what permissions they hold:

| Mode | User Provides | Fleet Creates | Use Case |
|------|---------------|---------------|----------|
| **New Project** | Goal only | New repo + team scaffold | Greenfield projects |
| **Owned Repo** | Repo URL (write access) | `fleeted/main` branch in same repo | User's own repo |
| **External Repo** | Repo URL (read-only) | New `fleeted-<name>` repo | Third-party repos |

### 1.1 New Project Mode

The user provides a goal only. Hermes Fleet creates a new repository
with a generated team scaffold (SOUL.md, policy.yaml, Docker Compose,
Kanban templates). This is the v0.1 flow.

```
User: "Build a SaaS MVP"
        ↓
Hermes Fleet: plan → generate → .fleet/
        ↓
Team: agents with roles, policies, isolation
```

### 1.2 Owned Repo Mode

The user provides a GitHub repository URL where they have **write
access**. No separate fleeted repo is needed. The fleet works inside
the same repository on isolated branches.

```
User: "Refactor the auth module of https://github.com/my-org/my-repo.git"
        ↓
1. Detect write permission → stay in same repo
2. Create fleeted/main branch (protected, no direct push)
3. Fingerprint source repo (lang, deps, CI, security posture)
4. Generate Team Proposal (fingerprint + goal → roles)
5. Open first issue → agent team begins PR-based work
│
All work: fleeted/* branches → PR → fleeted/main
Merge to main: requires human approval or high merge gate
```

Key properties:
- **No new repository** is created. The fleet works in the same repo.
- **`fleeted/main`** is the fleet's integration branch. All agent PRs
  target `fleeted/main`.
- **`main` is protected.** Direct push to `main` is forbidden for agents.
  Merging from `fleeted/main` to `main` requires human approval or a
  high-confidence merge gate decision.
- **Audit trail** (issues, PRs, reviews) stays in the same repository.
- **Source repo's existing CI/CD and secrets are visible.** The fleet
  can use existing CI, but must not modify deployment config or secrets.

### 1.3 External Repo Mode

The user provides a GitHub repository URL where they have **read-only
access** or must not modify the original. Hermes Fleet creates a new
fleeted repository as the workspace.

```
User: "Improve the security of https://github.com/NousResearch/hermes-agent.git"
        ↓
1. Detect read-only permission → create fleeted repo
2. Create fleeted-Caixa-git/fleeted-hermes-agent
3. Clone source (read-only reference)
4. Fingerprint source repo (lang, deps, CI, security posture)
5. Generate Team Proposal (fingerprint + goal → roles)
6. Open first issue → agent team begins PR-based work
│
All work: fleeted repo only. Source repo never modified.
```

Key properties:
- **New repository** is created (`fleeted-<source-name>`).
- **Source repo is read-only upstream.** Never cloned with write access.
- **Secrets, settings, Actions secrets, deployment config** are NOT
  copied. The fleeted repo starts empty of all sensitive configuration.
- **All work** happens in the fleeted repo.
- **Upstream contribution candidates** are documented in
  `FLEETED_EXIT_REPORT.md` for manual porting.

---

## 2. Naming and Branch Conventions

### 2.1 Owned Repo — Branch Naming (No New Repo)

In Owned Repo Mode, no new repository is created. The fleet uses branch
names within the existing repository:

| Convention | Example | Purpose |
|------------|---------|---------|
| `fleeted/main` | `fleeted/main` | Fleet integration branch. Protected, no direct push. |
| `fleeted/<agent-id>/<task-id>` | `fleeted/frontend-dev/TASK-042` | Agent working branches. All PRs target `fleeted/main`. |

Rules:
- `fleeted/main` is created on first `fleet ingest`. Protected branch:
  no direct push, no force push, requires PR for all changes.
- The original `main` branch is preserved unchanged by the fleet.
- Only the user (or an authorized human) can merge `fleeted/main` into
  `main`. The orchestrator may open a PR and label it
  `needs-human-approval`.
- `fleeted/*` branches are ephemeral. Deleted after PR merge.

### 2.2 External Repo — Repository Naming

In External Repo Mode, a new repository is created:

| Source | Fleeted Name | Owner |
|--------|--------------|-------|
| `NousResearch/hermes-agent` | `fleeted-hermes-agent` | `Caixa-git` |
| `user/repo` | `fleeted-repo` | `Caixa-git` |
| `org/project` | `fleeted-project` | `Caixa-git` or user-chosen org |

**Rules:**
- Prefix: `fleeted-` (configurable)
- The fleeted repo is created under the user's GitHub account or a
  designated organization
- The naming is deterministic from the source repo name
- A mapping file `.fleet/source-repo.yaml` stores the source URL and
  the fleeted repo URL

### 2.3 Permission Detection and Mode Selection

When a user provides a repo URL, the system detects the correct mode:

```text
1. Can we authenticate to the repo?
   ├── No  → External Repo Mode (read-only public clone)
   └── Yes →
2. Does the token have write access?
   ├── No  → External Repo Mode (read-only fork)
   └── Yes →
3. Does the user want a separate workspace?
   ├── Yes → External Repo Mode (explicit choice)
   └── No  → Owned Repo Mode (fleeted/main in same repo)
```

The decision is recorded in `.fleet/fleet.yaml`:

```yaml
mode: owned | external | new_project
source_repository: "https://github.com/org/repo.git"
source_access: write | read-only
fleeted_repository: ""  # empty for owned mode
fleeted_main_branch: "fleeted/main"
```

---

## 3. Source Repo Safety Boundaries

**The source repository is never modified by fleet agents.** This is a
hard rule. However, the boundary differs by mode:

### 3.1 Owned Repo Mode Boundaries

In Owned Repo Mode, the fleet works inside the same repository but on
isolated branches:

| Resource | Treatment |
|----------|-----------|
| `main` branch | Protected. No direct push, no agent force push. |
| `fleeted/main` branch | Fleet integration branch. All agent PRs target this. |
| `fleeted/*` branches | Agent working branches. Ephemeral, deleted after PR merge. |
| GitHub Secrets | Visible but must not be read or modified by agents. |
| GitHub Actions / CI | Fleet can trigger CI on `fleeted/*` branches. Must not modify workflow files. |
| Deployment config | Agents must not modify deployment files in any branch. |
| Issue tracker | Fleet creates issues and PRs in the same repo. |
| Settings / collaborators | Not modified. Branch protection for `fleeted/main` is set by the system. |

### 3.2 External Repo Mode Boundaries

In External Repo Mode, the source repo is completely isolated:

| Resource | Treatment |
|----------|-----------|
| Source code | Cloned as read-only reference. No commits, no branches, no pushes. |
| Secrets (GitHub Secrets, .env) | **Not copied.** Fleeted repo gets empty secrets. |
| GitHub Actions / CI config | Copied only if explicitly allowed by policy. Default: skip. |
| Deployment config | **Not copied.** Deployer agent starts disabled. |
| Issue tracker | **Not copied.** New issues are created in the fleeted repo. |
| Settings / collaborators | **Not copied.** Fleeted repo starts with default settings. |
| Wiki / Pages | **Not copied.** |

### 3.3 Common Rules (Both Modes)

- No agent may modify deployment config, CI/CD workflow files, or
  repository settings in any context.
- No agent may read or expose GitHub Secrets or environment variables
  containing credentials.
- The orchestrator audits all branches and PRs daily for boundary
  violations.

---

## 4. Repository Fingerprint

When a source repo is ingested, a **repository fingerprint** is generated
and stored in `.fleet/fingerprint.yaml`. The fingerprint is a structured
summary used to drive the Team Proposal.

```yaml
# .fleet/fingerprint.yaml
fingerprint:
  generated_at: "2026-05-03"
  source_repository: "https://github.com/NousResearch/hermes-agent.git"
  source_ref: "main"
  source_hash: "sha256:..."

  language:
    primary: "python"
    secondary: ["typescript", "shell"]
    package_manager: "uv/pip"

  framework:
    type: "cli"
    test: "pytest"
    test_count: 15000
    ci: "github-actions"

  complexity:
    files: 1200
    lines_of_code: 150000
    contributors: 50

  security_posture:
    has_security_policy: true
    has_dependabot: true
    has_codeql: false
    has_secret_scanning: true

  risk_flags:
    - "large codebase (150k+ lines)"      # impacts team size
    - "many contributors"                   # complex review cadence
    - "production deployment config present" # deployer must be disabled
    - "secrets detected in CI config"        # verify before enabling
```

The fingerprint is used by the Planner to recommend:

| Fingerprint Signal | Impact on Team Proposal |
|-------------------|------------------------|
| Language / framework | Role selection (Python → fullstack, backend, etc.) |
| Test count / CI type | QA Tester role — how many tests, what framework |
| Lines of code | Team scale — small (3 agents) vs large (9+ agents) |
| Security posture signals | Security Reviewer role strength, dependency audit |
| Risk flags | Deployer disabled, extra review stages |

---

## 5. Team Proposal from Repo + Goal

Given a repository fingerprint and a user goal, the Planner generates a
Team Proposal. The proposal is constrained by the Team Proposal schema
(see `SPEC.md` section 15.5).

```yaml
team_proposal:
  goal: "Improve security posture"
  recommended_team_id: "fleeted-security-audit"
  fingerprint_signals:
    - "large codebase → scale team to 5 agents"
    - "security scanning present → enable security reviewer"
    - "dependabot present → use existing dependency review"
  rationale: "Fingerprint indicates mature codebase with existing CI."
```

The proposal is validated before any fleet is deployed:

1. Does the recommended team exist in the contract inventory?
2. Are all required capabilities covered by the role inventory?
3. Is the fingerprint consistent with the source repo?
4. Does the proposal violate any safety constraints?

---

## 6. Workflow After Fleet Creation

Once the fleeted repo and team are created, the workflow is:

```
1. Orchestrator creates GitHub Issues in the fleeted repo
   │
2. Agents pick up issues, create branches
   │
3. Agents implement changes, push branches
   │
4. Agents create PRs against fleeted repo main
   │
5. Reviewers (agent or human) review PRs
   │
6. Merge Gate decides:
   ├── low-risk → auto-merge
   └── high-risk → human approval required
   │
7. Cycle repeats
```

### Key Rules

- **main direct push is forbidden.** Every change goes through a PR.
- **No changes flow back to the source repo.** The fleeted repo is
  the workspace. Changes can be manually ported to the source if
  the user explicitly approves.
- **Orchestrator opens issues.** Agents do not create their own issues.
  They find issues assigned to them and work on them.
- **Every PR has a handoff contract.** The agent that creates the PR
  includes a handoff note with required outputs from its role contract.

---

## 7. GitHub Audit Trail

All actions in the fleeted repo leave an audit trail on GitHub:

| Action | Artifact |
|--------|----------|
| Issue created by orchestrator | GitHub Issue with label, assignee |
| Agent starts work | Branch pushed, commit messages include task ID |
| Agent completes work | PR created with handoff note in body |
| Reviewer checks | Review comment thread on PR |
| Merge gate decision | PR comment: "Auto-merge approved" or "Requires human review" |
| Security violation | GitHub Issue labeled `security-incident` |

The audit trail serves as:

- **Human-readable history** of what the fleet did
- **Rollback reference** (each PR is a reversible unit)
- **Improvement data** for the fleet's own meta-analysis

---

## 8. Autonomy and Merge Gate

Not all PRs should auto-merge. The Merge Gate classifies each PR and
decides the merge strategy.

### Risk Classification

| Risk Level | Examples | Merge Policy |
|------------|----------|--------------|
| **Low** | Documentation, test additions, refactoring (no behavior change), dependency updates (patch) | Auto-merge after CI passes |
| **Medium** | New feature (non-critical), API additions, dependency updates (minor) | Auto-merge + require 1 reviewer approval |
| **High** | Security changes, database schema changes, dependency major updates, deployment config, secret management | **Human approval required** |

### Merge Gate Rules

1. Every PR must pass CI (tests, lint, build).
2. Every PR must include a handoff note from the creating agent.
3. Low-risk PRs auto-merge after CI passes.
4. Medium-risk PRs auto-merge after CI + 1 agent reviewer approval.
5. High-risk PRs are labeled `needs-human-approval` and wait for
   explicit user sign-off.
6. The Merge Gate never auto-merges a PR that touches:
   - `.env` or `*secret*` or `*token*` patterns
   - Deployment config (`Dockerfile`, `deploy/`, `k8s/`, `terraform/`)
   - CI/CD config (`.github/workflows/`, `.gitlab-ci.yml`)
   - Repository settings
7. Merge Gate outcomes are logged to the audit trail.

### Autonomy Escalation

If the Merge Gate blocks a PR for human approval:

1. The orchestrator labels the PR `needs-human-approval`.
2. The orchestrator sends a notification to the configured channel
   (GitHub notification, email, Telegram, etc.).
3. The system waits indefinitely for human response.
4. If the human rejects, the orchestrator closes the PR and creates
   a follow-up issue.
5. If the human approves, the PR merges and the next issue proceeds.

---

## 10. Community Signals

An existing open-source repository already has signals that reveal where
improvements are most valuable. Fleet Mode analyzes these signals before
intensifying the Team Proposal. The analysis must be **deterministic** —
fixed time windows, fixed weightings, no free-form "looks important"
decisions.

### 10.1 Signal Sources

| Source | What It Reveals |
|--------|----------------|
| **Issues** | User-reported bugs, feature requests, questions |
| **Discussions** | Architectural debates, design direction |
| **PRs** | Active development patterns, review cadence |
| **Release notes** | Project maturity, breaking changes, focus areas |
| **Labels** | Maintainer prioritization (bug, enhancement, help wanted) |
| **Stale issues** | Neglected areas, abandoned features |
| **User complaints** | Recurring pain points (duplicate issues, comment threads) |
| **Maintainer comments** | Explicit direction, blocked PRs, desired contributions |

### 10.2 Deterministic Analysis Rules

| Parameter | Default | Description |
|-----------|---------|-------------|
| `time_window_days` | 90 | Analyze issues/PRs from the last N days |
| `min_reaction_threshold` | 5 | Issue with 👍 reactions above this is "high community interest" |
| `stale_issue_days` | 365 | Issues with no activity in N days are "stale" |
| `label_priority_order` | `["bug", "security", "enhancement", "documentation", "question"]` | Priority for label-based task selection |
| `recurring_issue_min_duplicates` | 3 | If N+ issues describe the same problem, it's "recurring" |

### 10.3 Signal → Improvement Mapping

| Signal | Improvement Type |
|--------|-----------------|
| Many open bugs with 👍 reactions | Bug-fix sprint (QA Tester + Developer) |
| Stale dependency PRs | Dependency update (Developer, auto-merge low-risk) |
| Security advisories / Dependabot alerts | Security audit (Security Reviewer) |
| Missing or outdated documentation | Documentation pass (Technical Writer) |
| Recurring user complaints about a feature | UX improvement (UX Designer + Developer) |
| Abandoned PRs with partial work | Pickup and complete (Developer) |

### 10.4 Fingerprint Integration

Community signals augment the repository fingerprint:

```yaml
# Added to .fleet/fingerprint.yaml
community_signals:
  analyzed_at: "2026-05-03"
  time_window_days: 90

  issues:
    total_open: 45
    labeled_bug: 12
    labeled_enhancement: 18
    labeled_security: 3
    high_reaction_count: 5
    recurring_patterns:
      - "CLI crashes on large inputs"
      - "Configuration parsing errors"

  prs:
    total_open: 8
    stale_days_avg: 120
    abandoned_count: 3

  maintainer_signals:
    pinned_issues: ["Improve error messages", "Rewrite CLI parser"]
    recent_release_notes: ["v0.12.0 — Major refactor"]
```

---

## 11. Fleeted Exit Strategy

A fleeted repo is not an infinite improvement space. It is a workspace
with a clear goal and defined termination conditions. The Exit Strategy
determines when the fleet's work is complete.

### 11.1 Why an Exit Strategy

Without defined exit criteria, a fleeted run can continue indefinitely:

- There is always another issue to fix
- There is always another test to write
- There is always another refactoring opportunity
- Agents have no inherent sense of "done"

The Exit Strategy provides the stopping rule.

### 11.2 Exit Triggers

| Trigger | Meaning |
|---------|---------|
| **Goal completion** | All must-have and should-have items from the Team Proposal are resolved |
| **PR budget exhausted** | The fleet has a configured maximum PR count (default: 50). When reached, the fleet stops and reports. |
| **No low-risk high-value tasks remain** | Only high-risk, low-value, or maintainer-blocked tasks are left |
| **Next steps require human/maintainer decision** | Architecture decisions, new feature direction, or breaking changes that the fleet cannot decide autonomously |
| **Next steps require high-risk access** | Production secrets, deployment credentials, or infrastructure access that is intentionally withheld |
| **Source repo changed significantly** | The upstream source repo has diverged so much that the fingerprint is stale. A re-ingest may be needed. |

### 11.3 Exit Criteria Classification

Every fleeted run defines three categories of exit criteria at creation time:

| Category | Description | Example |
|----------|-------------|---------|
| **Must-have** | The fleet stops only when these are resolved | "Fix all critical security advisories" |
| **Should-have** | High priority, but the fleet can exit without them | "Improve test coverage to 80%" |
| **Stop-when** | Conditions that cancel the run early | "PR budget of 50 exhausted", "30 days without a merged PR" |
| **Human-approval-needed** | Tasks that must be escalated | "Deploy to production", "Change database schema", "Modify CI/CD pipeline" |

### 11.4 Exit Criteria Definition Format

```yaml
# .fleet/exit-strategy.yaml
exit_strategy:
  max_pr_count: 50
  max_duration_days: 90
  inactivity_timeout_days: 30

  must_have:
    - "resolve all critical security advisories"
    - "fix top 3 recurring bugs by duplicates count"

  should_have:
    - "improve test coverage to 80%"
    - "update all stale dependencies to latest minor"

  stop_when:
    - "pr_count >= max_pr_count"
    - "no PR merged in 30 days"
    - "source main branch advanced beyond fingerprint ref"

  human_approval_needed:
    - "any change to deployment configuration"
    - "any change to CI/CD pipeline"
    - "any change that introduces new dependencies on external services"
```

### 11.5 Exit Evaluation

The orchestrator evaluates exit criteria after every PR merge:

1. **Check must-haves.** Are all must-have items complete? If yes, flag
   "goal completion" as possible exit trigger.
2. **Check should-haves.** Report completion ratio (e.g., 3 of 5 done).
3. **Check stop-whens.** Has any stop condition been triggered?
4. **Check remaining tasks.** Classify remaining tasks by risk level.
5. **Recommend decision.** If must-haves are done AND only high-risk or
   human-approval items remain, recommend exit.
6. **Escalate to human.** The orchestrator creates a summary issue with
   the exit recommendation. The human decides: exit, continue, or adjust
   scope.

### 11.6 Mode-Specific Exit Behavior

The exit strategy behaves differently depending on mode:

| Aspect | Owned Repo Mode | External Repo Mode |
|--------|-----------------|-------------------|
| **Exit artifact location** | Committed to `fleeted/main` branch | Committed to fleeted repo root |
| **Source repo impact** | `fleeted/main` branch remains. Optionally open a PR to `main`. | No impact. Fleeted repo can be archived. |
| **Upstream contribution** | PR already exists in the same repo. Human reviews and merges. | PRs exist only in fleeted repo. Upstream candidates documented in exit report. |
| **Fleeted cleanup** | `fleeted/main` and `fleeted/*` branches can be deleted. | Entire fleeted repo can be archived or deleted. |
| **Exit report target** | Filed as an Issue and committed to `fleeted/main`. | Filed as an Issue and committed to fleeted repo root. |

In both modes, the exit report is the permanent record. The user decides
whether to keep, archive, or delete the fleeted workspace.

---

## 12. FLEETED_EXIT_REPORT.md

When a fleeted run stops (by any exit trigger), the orchestrator generates
`FLEETED_EXIT_REPORT.md` in the fleeted repo root. This document serves as
the permanent record of what the fleet accomplished.

### 12.1 Report Template

```markdown
# Fleeted Exit Report

## Source Repository
- URL: https://github.com/org/source-repo
- Ref at ingest: main@abc123
- Fingerprint generated: 2026-05-03

## Fleeted Repository
- URL: https://github.com/user/fleeted-source-repo
- Run duration: 45 days
- Exit trigger: goal completion

## Initial Goal
Improve the security posture of the source repository.

## Community Signals Analyzed
- 12 open bugs labeled "bug"
- 3 open security advisories
- 5 high-reaction issues
- 2 recurring bug patterns

## Improvements Merged
| # | PR | Description | Risk Level |
|---|-----|-------------|------------|
| 1 | #12 | Fix SQL injection in login endpoint | High |
| 2 | #15 | Update dependencies (patch) | Low |
| 3 | #18 | Add security.md and contribution guide | Low |
| 4 | #22 | Fix recurring crash on large input | Medium |

## PR List
- #12 Fix SQL injection (merged)
- #15 Dependency update (merged)
- #18 Security documentation (merged)
- #22 Crash fix (merged)
- #24 Auth rate limiting (open — requires human decision)

## Tests Run
- pytest: 15,234 passed, 3 failed (pre-existing)
- New tests added: 47

## Remaining Risks
- Rate limiting not implemented (requires human decision on throttling strategy)
- Database migration not attempted (high-risk, requires production access)

## Upstream Contribution Candidates
The following changes are suitable for upstream contribution:
- PR #12: SQL injection fix (port to source repo main)
- PR #18: Security documentation (port to source repo)

## Why the Fleeted Run Stopped
All must-have items from the exit strategy were resolved. Only high-risk
and human-approval items remain. The fleet cannot proceed without human
decision on rate limiting strategy and production database access.
```

### 12.2 Report Distribution

The exit report is:

1. Committed to the fleeted repo as `FLEETED_EXIT_REPORT.md`
2. Posted as a GitHub Issue summary in the fleeted repo
3. Sent to the configured notification channel (if any)

---

## 13. Relationship to Other Documents

| Document | Relationship |
|----------|-------------|
| `ARCHITECTURE.md` | Fleet Mode adds a new intake layer between "User Goal" and "Planner" |
| `SPEC.md` | Repository Fingerprint, Community Signals, Exit Strategy, and Merge Gate are new data types and components |
| `ROADMAP.md` | Fleet Mode is the organizing concept for v0.5-v0.6. Exit Strategy is part of the fleet lifecycle. |
| `WORKFLOW.md` | PR-based workflow, merge gate, and audit trail extend the work loop |
| `DESIGN_FOUNDATIONS.md` | Contract Net Protocol (CNP) governs the manager-contractor issue flow |
