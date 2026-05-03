# Hermes Agency — Technical Specification v0.1

---

## 1. Overview

Hermes Agency is a planning-layer tool for multi-agent work with Hermes Agent Kanban. It accepts a goal description, composes an appropriate team from agency-agents role specifications, generates per-role identity (SOUL.md) and boundaries (policy.yaml), and produces a task DAG that Kanban can execute.

It does **not** run agents, manage containers, or handle execution state. All execution is delegated to Hermes Agent Kanban.

---

## 2. Architecture

```
User Goal
    │
    ▼
┌─────────────────────────────────────────────────┐
│                  Planner                         │
│  (keyword heuristic → team recommendation)       │
│  (task decomposition → DAG construction)         │
└──────┬──────────────────────────────────────────┘
       │
       ▼
┌─────────────────────────────────────────────────┐
│                  Generator                       │
│  SOUL.md per role (f-string templates)           │
│  policy.yaml per role (permission preset merge)  │
│  Handoff contract I/O schemas                    │
└──────┬──────────────────────────────────────────┘
       │
       ▼
┌─────────────────────────────────────────────────┐
│              Kanban Bridge (v0.2+)               │
│  plan → kanban_create() calls                    │
│  skills=[SOUL.md, policy.yaml] per task           │
│  parents=dependency edges                         │
└─────────────────────────────────────────────────┘
       │
       ▼
┌─────────────────────────────────────────────────┐
│           Hermes Agent Kanban                    │
│  (dispatcher, worker pool, state machine,        │
│   failure handling, workspace management)        │
└─────────────────────────────────────────────────┘
```

### Layers

#### 2.1 Definition Layer — `presets/`

Static YAML files that define available teams, roles, and permission presets.

| Path | Contents |
|------|----------|
| `presets/teams/` | Team compositions: which roles belong to which team |
| `presets/roles/` | Role definitions: identity, mission, allowed/forbidden work, permissions |
| `presets/permissions/` | Permission presets: reusable filesystem/network/secret rules |

#### 2.2 Schema Layer — `src/hermes_agency/contracts.py`

Pydantic models for all data structures:
- `TeamContract` — team ID, name, agent list, optional agents
- `RoleContract` — role ID, source provenance, fidelity mode, tasks, permissions
- `PermissionPresetContract` — workspace, repo_write, secrets, network
- `HandoffContract` — I/O schemas: required input fields, required output fields, validation rules
- `FoundationLock` / `AgencyLock` — lock file schemas
- `PlanOutput` — complete plan: team, agents (with SOUL.md + policy.yaml), task DAG

#### 2.3 Planning Layer — `src/hermes_agency/planner.py`

Goal → team recommendation → task decomposition:

- Parse goal text for keywords
- Match against team descriptions (heuristic, v0.1)
- Decompose goal into ordered task steps
- Return `PlanOutput`: team ID, agent roster, task DAG with dependencies

**Foundation-bound**: The planner operates within the constraints of `foundation.lock.yaml` and `agency.lock.yaml`. It does not invent roles or principles beyond what the locks define.

#### 2.4 Generator Layer — `src/hermes_agency/generator.py`

Role identity + boundary generation:

- Load team definition → resolve roles → assemble agent configs
- Render SOUL.md from f-string templates (identity, mission, non-goals, handoff contract)
- Render policy.yaml from role definition + permission preset merge
- Output: per-agent SOUL.md + policy.yaml

#### 2.5 Kanban Bridge — `src/hermes_agency/kanban_bridge.py` (v0.2+)

Plan → Kanban task registration:

- For each task in DAG: call `kanban_create` with assignee, body, parents, skills (SOUL.md + policy.yaml)
- Return task IDs for tracking

#### 2.6 CLI — `src/hermes_agency/cli.py`

| Command | v0.1 | v0.2+ |
|---------|------|-------|
| `init` | Create `.fleet/` project scaffold | Same |
| `plan` | Goal → report (team + agents + DAG) | Same |
| `apply` | — | Plan → Kanban tasks |
| `agency fetch/diff/update` | — | agency-agents import workflow |

---

## 3. CLI Commands

### 3.1 `hermes-agency init`

Creates local project configuration.

```
Usage: hermes-agency init [OPTIONS]

Options:
  --dir TEXT   Project directory (default: cwd)
  --help       Show help
```

Creates:
- `.fleet/fleet.yaml` — project configuration
- `.fleet/foundation.lock.yaml` — design foundation lock
- `.fleet/agency.lock.yaml` — agency-agents version lock

### 3.2 `hermes-agency plan <goal>`

Analyzes a goal and recommends a team with task DAG.

```
Usage: hermes-agency plan [OPTIONS] GOAL

Arguments:
  GOAL  Description of the work to be done

Options:
  --show-details   Show full agent roster, permissions, and task DAG
  --output FILE    Write plan as YAML to file
  --help           Show help
```

Returns:
- Recommended team ID + name
- Agent roster: each agent with assigned role, SOUL.md path, policy.yaml path
- Task DAG: ordered steps showing dependencies between agents

**Keyword heuristics** (v0.1):

| Keywords | Team |
|----------|------|
| "saas", "subscription", "dashboard", "auth", "billing", "web app", "api" | `saas-medium` |
| "ios", "iphone", "apple", "swift", "mobile app" | `iphone-app` |
| "ai", "machine learning", "llm", "rag", "chatbot", "gpt" | `ai-app` |
| "security audit", "penetration test", "vulnerability" | `security-audit` |
| "research", "whitepaper", "literature review", "study" | `research-writing` |
| "content", "blog", "marketing", "social media" | `content-creator` |
| "devops", "ci/cd", "deployment", "terraform", "kubernetes" | `devops-deployment` |
| Everything else | `general-dev` |

### 3.3 `hermes-agency apply` (v0.2+)

Registers a plan with Hermes Agent Kanban.

```
Usage: hermes-agency apply [OPTIONS]

Options:
  --plan FILE    Plan YAML file (default: .fleet/plan.yaml)
  --dry-run      Show what would be created without creating
  --help         Show help
```

Calls `kanban_create` for each task in the DAG with:
- `assignee` → agent role ID
- `body` → task description + SOUL.md reference
- `skills` → [SOUL.md content, policy.yaml content]
- `parents` → dependency task IDs
- `workspace_kind` → based on role permission preset

---

## 4. Team Presets

### 4.1 General Development (`general-dev`)

**Purpose**: Small, general-purpose team for ordinary software tasks.

**Agents**: orchestrator, fullstack-developer, reviewer, qa-tester, technical-writer

### 4.2 Medium SaaS (`saas-medium`)

**Purpose**: Balanced team for a SaaS MVP.

**Agents**: orchestrator, product-manager, ux-designer, frontend-developer, backend-developer, database-architect, qa-tester, security-reviewer, technical-writer

**Optional**: deployer

### 4.3 iOS App (`iphone-app`)

**Purpose**: Native iOS development.

**Agents**: orchestrator, frontend-developer, reviewer, qa-tester

### 4.4 AI/ML App (`ai-app`)

**Purpose**: LLM-powered applications, RAG systems.

**Agents**: orchestrator, frontend-developer, backend-developer, reviewer, qa-tester, technical-writer

### 4.5 Security Audit (`security-audit`)

**Purpose**: Code security review, vulnerability assessment.

**Agents**: orchestrator, security-reviewer, reviewer

### 4.6 Research & Writing (`research-writing`)

**Purpose**: Technical papers, literature reviews.

**Agents**: orchestrator, technical-writer, reviewer

### 4.7 Content Creator (`content-creator`)

**Purpose**: Blog posts, marketing, SEO.

**Agents**: orchestrator, technical-writer, reviewer

### 4.8 DevOps Deployment (`devops-deployment`)

**Purpose**: CI/CD, infrastructure, deployment.

**Agents**: orchestrator, deployer, reviewer

---

## 5. Output Format: Plan

```yaml
plan:
  goal: "Build a SaaS MVP with subscription billing"
  team_id: saas-medium
  team_name: "Medium SaaS Team"
  agents:
    - role_id: orchestrator
      name: Orchestrator
      soul_md_path: .fleet/plan/agents/orchestrator/SOUL.md
      policy_yaml_path: .fleet/plan/agents/orchestrator/policy.yaml
    - role_id: frontend-developer
      name: Frontend Developer
      # ...
  task_dag:
    - step: 1
      assignee: product-manager
      title: "Define product requirements and user stories"
      description: "Based on goal, create PRD with user stories for subscription billing"
      parents: []
    - step: 2
      assignee: ux-designer
      title: "Design UI mockups for subscription flow"
      description: "Create wireframes for pricing page, signup flow, account management"
      parents: [step_1]
    - step: 3
      assignee: backend-developer
      title: "Implement billing API and subscription logic"
      description: "Stripe integration, plan management, webhook handlers"
      parents: [step_1]
    # ...
  handoff_contracts:
    - from: product-manager
      to: frontend-developer
      required_output: [prd, user_stories, acceptance_criteria]
      required_input: []
```

---

## 6. Permission Presets

| ID | Workspace | Repo Write | Secrets | Network |
|----|-----------|------------|---------|---------|
| `orchestrator_safe` | kanban_only | false | [] | control_plane_only |
| `repo_readonly` | readonly | false | [] | none |
| `docs_rw_repo_ro` | docs_write | false | [] | none |
| `frontend_worktree_rw` | own_worktree_rw | true | PUBLIC_ONLY | package_registry |
| `backend_worktree_rw` | own_worktree_rw | true | DEV_ONLY | package_registry |
| `schema_worktree_rw` | own_worktree_rw | true | DATABASE_URL_DEV | package_registry |
| `readonly_no_network` | readonly | false | [] | none |
| `test_runner` | readonly_or_test_tmp | false | [] | none |

---

## 7. Package Structure

```
hermes-agency/
├── README.md
├── ROADMAP.md
├── SPEC.md
├── ARCHITECTURE.md
├── DESIGN_FOUNDATIONS.md
├── LICENSE
├── pyproject.toml
├── src/
│   └── hermes_agency/
│       ├── __init__.py
│       ├── cli.py
│       ├── contracts.py
│       ├── planner.py
│       ├── teams.py
│       ├── generator.py
│       ├── policy.py
│       ├── kanban_bridge.py    # v0.2+
│       └── __init__.py
├── presets/
│   ├── teams/
│   ├── roles/
│   └── permissions/
└── tests/
```

---

## 8. Technical Stack

- **Language**: Python 3.10+
- **CLI**: Typer
- **Schema**: Pydantic
- **Templates**: Python f-strings
- **Testing**: pytest
- **Kanban API**: Hermes Agent kanban tools (`kanban_create`, `kanban_show`, etc.)

---

## 9. Output Determinism

All generated output must be deterministic:

- No timestamps in generated files
- No random UUIDs (task IDs come from Kanban, not from agency)
- Stable ordering of agents, policy fields, and roles
- Same input → same team, same DAG, same SOUL.md, same policy.yaml

---

## 10. Non-Goals

- Running agents or containers
- Managing execution state
- Replacing any Kanban functionality
- Container orchestration
- Network configuration
- Secret management
- Runtime policy enforcement
- Web dashboard or UI
