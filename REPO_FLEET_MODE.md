# Hermes Fleet — Repo Fleet Mode

> **Status**: Design document (not yet implemented). Targeted for v0.5+.
>
> This document describes how Hermes Fleet ingests an existing repository
> and creates an isolated "fleeted" workspace where an agent team can
> autonomously improve the codebase through PR-based collaboration.

---

## 1. Two Modes

Hermes Fleet supports two starting modes:

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

See `ARCHITECTURE.md` and `SPEC.md` for the current implementation.

### 1.2 Existing Repo Mode (Fleet Mode)

The user provides a GitHub repository URL and a goal. Hermes Fleet:

1. Clones the source repo as a **read-only reference**
2. Creates a new **fleeted repository** as the workspace
3. Generates a **repository fingerprint** from the source
4. Generates a **Team Proposal** from the fingerprint + goal
5. Opens the first issue to start work

```
User: "Improve the security of https://github.com/NousResearch/hermes-agent.git"
        ↓
1. Clone source (read-only reference)
2. Create fleeted-Caixa-git/fleeted-hermes-agent
3. Fingerprint source repo (lang, deps, CI, security posture)
4. Generate Team Proposal (fingerprint + goal → roles)
5. Open first issue → agent team begins PR-based work
```

---

## 2. Fleeted Repository Naming

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

---

## 3. Source Repo Safety Boundaries

**The source repository is never modified.** This is a hard rule.

| Resource | Treatment |
|----------|-----------|
| Source code | Cloned as read-only reference. No commits, no branches, no pushes. |
| Secrets (GitHub Secrets, .env) | **Not copied.** Fleeted repo gets empty secrets. |
| GitHub Actions / CI config | Copied only if explicitly allowed by policy. Default: skip. |
| Deployment config | **Not copied.** Deployer agent starts disabled. |
| Issue tracker | **Not copied.** New issues are created in the fleeted repo. |
| Settings / collaborators | **Not copied.** Fleeted repo starts with default settings. |
| Wiki / Pages | **Not copied.** |

The fleeted repo starts as a clean fork of the source with **no
automation, no secrets, no deployment config, and no access to
production infrastructure.**

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

## 9. Relationship to Other Documents

| Document | Relationship |
|----------|-------------|
| `ARCHITECTURE.md` | Fleet Mode adds a new intake layer between "User Goal" and "Planner" |
| `SPEC.md` | Repository Fingerprint is a new data type; Merge Gate is a new component |
| `ROADMAP.md` | Fleet Mode is the organizing concept for v0.5-v0.6 |
| `WORKFLOW.md` | PR-based workflow, merge gate, and audit trail extend the work loop |
| `DESIGN_FOUNDATIONS.md` | Contract Net Protocol (CNP) governs the manager-contractor issue flow |
