# Hermes Fleet — Design Foundations

> This document defines the frozen design foundations that underpin the
> deterministic team composition system. These sources change slowly,
> through a strict proposal → impact analysis → regression test →
> human approval → version bump process.

---

## 1. Purpose

Hermes Fleet is built on one non-negotiable principle: **every agent is isolated**.

No agent can see another agent's memory, files, network, or secrets. No agent can talk to another agent directly. Even the user cannot talk to sub-agents directly. Every message, every piece of data, every network request must pass through **the orchestrator** — the sole entity that holds all the keys.

From this single pillar, four facets emerge — **Role**, **Boundary**, **Completion**, **Orchestrator** — grounded in four academic and standards-based foundation sources documented below.

Team composition must be **deterministic** and **grounded**.
The same input, the same locked foundation ref, the same agency-agents ref,
and the same mapping table must always produce the same Team Proposal.

To guarantee this, we distinguish two kinds of dependencies:

| Layer | Example | Update Cadence | Lock File |
|-------|---------|----------------|-----------|
| **Foundations** | Academic papers, standards (RBAC, CNP) | Months to years | `foundation.lock.yaml` |
| **Role Inventory** | agency-agents role definitions | Weeks to months | `agency.lock.yaml` |

An onboarding AI is a **foundation-bound planner**. It synthesizes teams
within the boundaries of the locked foundations and the locked role
inventory. It does not improvise new principles, new role taxonomies, or
new handoff protocols beyond what the locks allow.

---

## 2. Foundation Sources (v1)

### 2.1 Agent-Oriented Planning in Multi-Agent Systems

**Reference**: Classic multi-agent planning literature (e.g., Wooldridge,
Jennings, Rao, Georgeff foundations of agent-oriented planning).

**Core concepts applied in Hermes Fleet**:

| Pillar | Concept | Application |
|--------|---------|-------------|
| Role | **Solvability** | Can the team's composition solve the stated goal? The Team Contract's `required_capabilities` must be covered by the `role_inventory`. If a required capability has no assigned role, the team is incomplete. |
| Role | **Completeness** | Are all necessary roles present? No gaps between goal requirements and team composition. |
| Role | **Non-redundancy** | No unnecessary roles. Every role in the team must map to at least one required capability. Optional roles are disabled by default. |

These three concepts govern the Team Proposal validation gates. A proposal
that fails solvability, completeness, or non-redundancy is rejected before
generation begins.

### 2.2 LLM-based Multi-Agent Systems Survey

**Reference**: Survey taxonomies of LLM-based multi-agent systems (profile,
perception, self-action, mutual interaction, evolution).

**Core concepts applied in Hermes Fleet**:

| Pillar | Concept | Application |
|--------|---------|-------------|
| Role | **Profile** | SOUL.md defines each agent's identity, mission, non-goals, and behavioral constraints. This is the agent's public persona. |
| Boundary | **Perception** | policy.yaml defines what an agent can see (filesystem paths, network endpoints, secrets). Perception is bounded by policy. |
| Boundary | **Self-action** | Each agent operates autonomously within its allowed work scope. It does not exceed its role boundaries without handoff. |
| Completion | **Mutual interaction** | Handoff contracts define how agents communicate. Interaction is structured, validated, and auditable. |
| Role | **Evolution** | agency-agents updates bring new or improved role definitions. The update process preserves existing contracts and gates new roles. |

### 2.3 NIST RBAC / Sandhu RBAC

**Reference**: NIST RBAC standard (ANSI INCITS 359) and Sandhu et al.,
"Role-Based Access Control Models" (IEEE Computer, 1996).

**Core concepts applied in Hermes Fleet**:

| Pillar | Concept | Application |
|--------|---------|-------------|
| Boundary | **Least privilege** | Every agent starts with the minimum permissions required for its role. No agent has access it does not need. |
| Boundary | **Role-permission mapping** | Permission presets map roles to filesystem, network, secret, and command permissions. The mapping is explicit and auditable. |
| Role / Boundary | **Separation of duties** | No single agent should have conflicting roles. A security reviewer cannot also be an implementer. An orchestrator cannot write application code. These constraints are encoded in `forbidden_task_types` and `forbidden_paths`. |

### 2.4 Contract Net Protocol (CNP)

**Reference**: Smith, "The Contract Net Protocol: High-Level Communication
and Control in a Distributed Problem Solver" (IEEE Trans. Computers, 1980).

**Core concepts applied in Hermes Fleet**:

| Pillar | Concept | Application |
|--------|---------|-------------|
| Completion | **Task contract** | Every task between agents is a formal contract with required inputs, required outputs, and validation rules. |
| Completion | **Manager-contractor assignment** | The orchestrator acts as manager. Task contracts define who assigns (orchestrator), who executes (contractor), and who reviews (reviewer/security). |
| Completion | **Structured reporting** | Handoff notes follow a fixed template with role-specific required fields. Completion gates validate that reporting is complete before the task is delivered. |
| Completion | **Human verification** | In runtime (v0.5+), the orchestrator aggregates sub-agent results and presents them to the user. User approval is the final completion gate. The orchestrator is the CNP manager extended with a human principal. |

---

## 3. Foundation Lifecycle

### 3.1 Locking

Foundation sources are pinned to specific versions in `.fleet/foundation.lock.yaml`:

```yaml
# .fleet/foundation.lock.yaml
foundation_version: 1
sources:
  - id: agent_oriented_planning
    version: "v1"
    locked_at: "2026-05-03"
  - id: llm_mas_survey
    version: "v1"
    locked_at: "2026-05-03"
  - id: nist_rbac
    version: "v1"
    locked_at: "2026-05-03"
  - id: contract_net_protocol
    version: "v1"
    locked_at: "2026-05-03"
```

### 3.2 Update Procedure

Changing a foundation source requires a stricter process than changing
agency-agents:

```
1. Proposal     ──► Document which foundation source to update and why
2. Impact analysis ──► Assess which Team Contracts, Role Contracts, and
                       Handoff Contracts are affected
3. Deterministic regression test ──► Run all 5 test categories.
                                     Verify unchanged inputs still produce
                                     identical outputs.
4. Human approval ──► Explicit sign-off. No auto-promote.
5. Version bump  ──► Increment foundation_version in foundation.lock.yaml.
                     Update DESIGN_FOUNDATIONS.md with new source version.
```

### 3.3 Foundation-Bound Planner

The Planner (whether keyword-based in v0.1 or AI-powered in v0.2+) is
**foundation-bound**. This means:

- It synthesizes team proposals within the boundaries of the locked
  foundations and the locked role inventory.
- It does not invent new principles, role taxonomies, or handoff protocols
  beyond what the locks allow.
- Its output is constrained to the `Team Proposal` schema (see SPEC.md
  section 15.5).
- If a new research paper proposes a better team composition strategy,
  the planner does not adopt it automatically. The paper must go through
  the foundation update process first.

### 3.4 Determinism Guarantee

Given the same inputs:

```
goal: "Build a SaaS MVP"
foundation.lock.yaml: foundation_version = 1
agency.lock.yaml: ref = v1.2.0
mapping_table: (unchanged)
```

The same Team Proposal must be produced. Always.

This guarantee holds regardless of:
- Which AI model is used (v0.2+)
- The current date or time
- Random seeds
- Network conditions
- Prior session state
