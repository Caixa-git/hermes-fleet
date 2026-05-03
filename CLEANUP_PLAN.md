# Hermes Fleet — Documentation Cleanup Plan

> **Status**: Planning document. No files have been moved, deleted, or rewritten.
>
> This document audits all product documentation against the
> **Role / Boundary / Completion** framework and the "simple knife" principle.
> It proposes cuts, compressions, and moves — but does not execute them.

---

**Core Philosophy**
> A simple knife is the most deadly.

**One-sentence definition**
> Hermes Fleet gives every agent a role to preserve, a boundary it cannot
> cross, and a completion contract it must satisfy. v0.1 is a generator and
> validator — nothing more.

---

## 1. Current State

### Document Inventory (root directory, 16 files)

```
ROOT
├── Product Core (7)
│   ├── README.md                      # ~200 lines — entry point
│   ├── ROADMAP.md                     # ~222 lines — version plan
│   ├── ARCHITECTURE.md                # ~515 lines — system design
│   ├── SPEC.md                        # ~773 lines — technical spec
│   ├── DESIGN_FOUNDATIONS.md          # ~166 lines — academic grounding
│   ├── WORKFLOW.md                    # ~628 lines — contributor guide
│   └── REPO_FLEET_MODE.md             # ~278 lines — future design (root!)
│
├── Historical / Bootstrap (6)
│   ├── GIT_PLAN.md                    # ~293 lines — first git init plan
│   ├── GITHUB_SETUP_PLAN.md           # ~135 lines — remote setup plan
│   ├── PATCH_PLAN.md                  # ~242 lines — patch plan from review
│   ├── REVIEW_REPORT.md               # ~182 lines — code review output
│   ├── TEST_RESULTS.md                # ~120 lines — test run summary
│   └── RESEARCH_NOTES.md              # ~217 lines — pre-v0.1 research
│
├── Planning / Active (2)
│   ├── CLEANUP_PLAN.md                # This file — current planning
│   └── PATCH_PLAN.md                  # Already listed above (historical)
│
├── Future Design (2)
│   ├── docs/design/                    # Directory (may not exist yet)
│   │   └── AGENT_ACCOUNTABILITY_PROTOCOL.md  # ~613 lines — AAP design
│   └── REPO_FLEET_MODE.md             # At root — should be in docs/design/
│
└── Infrastructure (2)
    ├── pyproject.toml
    └── .gitignore
```

**Total**: ~4,600 lines of documentation across 13 markdown files (excluding
this plan and infra files).

### Role / Boundary / Completion Reflection Status

| Pillar | README | ARCHITECTURE | SPEC | DESIGN_FOUNDATIONS | ROADMAP |
|--------|--------|--------------|------|--------------------|---------|
| **Role** | ✅ Clean, key question | ✅ Clean, artifact table | ✅ Clean, artifact list | ✅ Pillar column | ✅ Strengthens annotation |
| **Boundary** | ✅ Clean | ✅ Clean | ✅ Clean | ✅ Pillar column | ✅ Strengthens annotation |
| **Completion** | ✅ Clean, Done= | ✅ Clean, Done= | ✅ Clean, Done= | ✅ Pillar column | ✅ Strengthens annotation |

**All five product docs are now consistent with the three-pillar framework.**

### Remaining Old Terminology

| Old Term | Location | Suggested Action |
|----------|----------|------------------
| "Role Fidelity" | ROADMAP.md v0.2 title | Keep — feature name, not pillar |
| "Role Fidelity" | ROADMAP.md v0.2 subsection | Keep — feature name |
| "Isolation audit" | ROADMAP.md v0.4 | Keep — feature name |
| "Handoff" (as pillar) | None remaining | ✅ Already updated |
| "Role Fidelity" (as pillar) | None remaining | ✅ Already updated |

**No pillar-name inconsistencies remain across product docs.**

### Over-Promise / Future-as-Current Risks

| Risk | File | Severity |
|------|------|----------|
| Fleet Mode architecture diagram (v0.5+) in current ARCHITECTURE.md | ARCHITECTURE.md §Fleet Mode Architecture (v0.5+) | Medium — clearly labeled v0.5+ but takes up ~30 lines |
| Contract Architecture with detailed YAML schemas (v0.2+) | ARCHITECTURE.md §Contract Architecture (v0.2+) | Medium — detailed YAML examples of future schemas |
| Fleet Mode, GitHub runtime, AAP, auto-merge governance | SPEC.md §13 (Fleet Mode), §14 (Agency Update), §15 (Contract Schemas) | High — 200+ lines of speculative future spec |
| ROADMAP v0.5+ detailed sub-items | ROADMAP.md §v0.5, §v0.6 | Low — clearly versioned but very detailed for far future |
| Jinja2 reference in RESEARCH_NOTES.md §6 | RESEARCH_NOTES.md (historical) | Low — historical doc, will move to docs/history/ |
| "Execute Hermes agents" says "Not yet (v0.3)" | README.md What v0.1 Does table | Low — accurate |

---

## 2. Product Core

### One-Sentence Definition (for every major doc)

> **Hermes Fleet is a generator and validator that creates secure, role-based
> Hermes Agent team configurations. v0.1 generates configuration only — it
> does not execute agents or require an existing Hermes installation.**

### Minimum Concepts a User Must Know

1. **Role** — Each agent gets a SOUL.md with a preserved role identity
2. **Boundary** — Each agent gets a policy.yaml + Docker Compose enforcing
   filesystem, network, and secret limits
3. **Completion** — Handoffs are role-specific contracts with validation gates
4. **Safe defaults** — 21 checks verify generated output is conservative
5. **Deterministic** — Same input → same output, every time

### v0.1 / v0.2 Core Features

| Feature | v0.1 | v0.2 |
|---------|------|------|
| CLI: init, plan, generate, test safe-defaults | ✅ | ✅ |
| Team presets (general-dev, saas-medium) | ✅ | ✅ + more |
| Role presets with permissions | ✅ | ✅ + agency-agents import |
| SOUL.md generation | ✅ | ✅ + provenance metadata |
| policy.yaml generation | ✅ | ✅ |
| Docker Compose generation | ✅ | ✅ |
| Kanban handoff templates | ✅ | ✅ |
| Safe-defaults validator (21 checks) | ✅ | ✅ + more checks |
| Contract schemas (Team/Role/Handoff) | ❌ | ✅ |
| agency-agents preserve compiler | ❌ | ✅ |
| foundation.lock + agency.lock | ❌ | ✅ |

---

## 3. Document-by-Document Findings

### 3.1 README.md

**Status**: ✅ Good. Clean, focused, Role/Boundary/Completion aligned.

**Issues**: None critical. Minor observations:
- `What v0.1 Does` table and `What This Project Is / Is Not` partially overlap
- "21 safe-default rules" — actual count is 20 pass + 1 skip (Docker Compose generation when compose only has 1 service). This is a minor numerical inconsistency.
- Quickstart and Example Flow sections have different length examples but cover the same flow — could merge

**Recommendation**: Very minor. Keep as-is or combine What-v0.1-Does table with the Is/Is-Not list into a single compact section.

### 3.2 ROADMAP.md

**Status**: ✅ Good. Role/Boundary/Completion Strengthens annotations added.

**Issues**: 

| Issue | Detail | Severity |
|-------|--------|----------|
| v0.5+ Fleet Mode is very detailed | 30+ lines of sub-items for v0.5+ future | Low |
| v0.6 Orchestrator Integration | Entire section for a speculative version | Low |
| v1.0 roadmap | 11 line items, some aspirational | Low |
| v0.2 "Role Fidelity" subsection title | Feature name, not pillar — fine to keep | None |

**Recommendation**: Compress v0.5+ into a single "Future" section with brief
bullet points instead of detailed sub-sections. Keep v0.1-v0.4 detailed since
they're near-term.

### 3.3 ARCHITECTURE.md

**Status**: ⚠️ Mixed. Core Pillars section is clean. Future sections at bottom
are speculative but clearly version-labeled.

**Issues**:

| Issue | Lines | Detail | Severity |
|-------|-------|--------|----------|
| Fleet Mode Architecture (v0.5+) | ~308-346 | Detailed architecture diagram and components for a future feature. Labeled "v0.5+" but takes up space | Medium |
| Contract Architecture (v0.2+) | ~347-500 | Full YAML schemas for Team/Role/Handoff Contracts and Team Proposal. 150+ lines of future spec that doesn't exist in code yet | Medium |
| Future Architecture (v0.3+) | ~253-280 | Fleet Runtime diagram with Policy Enforcer and Audit Logger — clearly future but mixed into current architecture doc | Low |
| Agency-Agents Update Model | ~282-304 | Detailed 8-step update process for a v0.2 feature | Medium |

**Recommendation**: Move Contract Architecture, Fleet Mode, and Agency-Agents
Update sections out of the current ARCHITECTURE.md. Either:
- Trim them to brief one-paragraph references with links to dedicated design docs
- Or keep them but clearly separate under a "## Future Architecture" header
  with a strong separator

The safest cut: replace the detailed YAML schemas in §Contract Architecture
with a short paragraph and a link to `docs/design/` or SPEC.md (where they
already live more spec-appropriately).

### 3.4 SPEC.md

**Status**: ⚠️ Heavy. Contains 200+ lines of speculative future spec that
reads like current implementation.

**Issues**:

| Issue | Lines | Detail | Severity |
|-------|-------|--------|----------|
| §13 Fleet Mode | ~510-560 | Complete spec for a v0.5+ feature | High |
| §14 Agency Update | ~560-590 | 8-step update workflow, detailed | Medium |
| §15 Contract Schemas | ~590-770 | Full YAML examples for contracts not yet implemented. Lists validation rules, enumerations, etc. | High |

These sections were added during the v0.2 contract design work. They contain
detailed YAML examples (Team Contract, Role Contract, Handoff Contract,
Team Proposal) with validation rules, enumerations, and completion gate
definitions.

**Recommendation**: 
- §13 Fleet Mode → move to `docs/design/` or compress to 2-3 sentences
- §14 Agency Update → move to `docs/design/` or compress to reference
- §15 Contract Schemas → keep as v0.2 design reference but trim YAML
  examples to minimal stubs; full schemas belong in `docs/design/`

### 3.5 DESIGN_FOUNDATIONS.md

**Status**: ✅ Good. Pillar column added, clean academic grounding.

**Issues**: None. This is a reference document. The foundation sources and
their pillar mappings are correct.

**Recommendation**: No changes needed.

### 3.6 WORKFLOW.md

**Status**: ⚠️ Long but valuable. 628 lines for a contributor guide.

**Issues**:

| Issue | Lines | Detail | Severity |
|-------|-------|--------|----------|
| §9 Initial Git Cleanup Plan | ~399-500+ | Bootstrap instructions for a git repo that was set up weeks ago. Contains `git init` commands, initial commit decisions, etc. | Medium |
| Length | 628 lines | Good content but very long for a workflow guide | Low |
| Mix of contributor and user content | Throughout | Sections 1-8 are contributor workflow; §9 is historical bootstrap | Medium |

**Recommendation**:
- Move §9 (Initial Git Cleanup Plan) to `docs/history/`
- The rest of WORKFLOW.md (Sections 1-8) is valuable contributor guidance
  and should stay at root

### 3.7 Root Historical Docs

| File | Lines | Content | Recommendation |
|------|-------|---------|----------------|
| `GIT_PLAN.md` | 293 | Pre-git-init planning, file inventory, first commit strategy | Move to `docs/history/` |
| `GITHUB_SETUP_PLAN.md` | 135 | GitHub remote setup, pre-push verification | Move to `docs/history/` |
| `PATCH_PLAN.md` | 242 | Patch plan from v0.1 code review | Move to `docs/history/` |
| `REVIEW_REPORT.md` | 182 | Code review findings (M1, L1-L6, etc.) | Move to `docs/history/` |
| `TEST_RESULTS.md` | 120 | Test run summary with 76 tests | Move to `docs/history/` |
| `RESEARCH_NOTES.md` | 217 | Pre-v0.1 research on Hermes, agency-agents, landscape | Move to `docs/history/` |

**Total historical lines**: ~1,189 lines (26% of all documentation).

**Rationale for moving**: These documents were written during the initial
v0.1 bootstrap and review cycle. They contain setup instructions, review
findings, and planning notes that are valuable as project history but not
relevant to users or contributors reading the product docs.

### 3.8 Future Design Docs

| File | Location | Content | Recommendation |
|------|----------|---------|----------------|
| `AGENT_ACCOUNTABILITY_PROTOCOL.md` | `docs/design/` ✅ | AAP design (~613 lines) | Already in right place |
| `REPO_FLEET_MODE.md` | Root ❌ | Fleet Mode design (~278 lines) | Move to `docs/design/` |

---

## 4. Cut / Compress / Move Candidates

### Delete Candidates

None. No document is completely worthless. Every file has historical or
reference value. The right action is move or compress, not delete.

### Compress Candidates

| Doc | Current | Target | Rationale |
|-----|---------|--------|-----------|
| ARCHITECTURE.md §Contract Architecture | ~150 lines | ~30 lines | Replace detailed YAML schemas with short description + link to SPEC.md or docs/design/ |
| ARCHITECTURE.md §Fleet Mode | ~40 lines | ~10 lines | Trim to brief reference; full design is in REPO_FLEET_MODE.md |
| ARCHITECTURE.md §Agency-Agents Update | ~25 lines | ~10 lines | Trim to summary |
| ROADMAP.md v0.5+ | ~60 lines | ~20 lines | Merge v0.5/v0.6/v1.0 into "Future" section |
| SPEC.md §13 Fleet Mode | ~50 lines | Remove | Move to docs/design/ or replace with brief reference |
| SPEC.md §14 Agency Update | ~30 lines | Remove | Move to docs/design/ |
| SPEC.md §15 Contract Schemas | ~180 lines | ~40 lines | Trim to minimal stubs; full schemas to docs/design/ |
| WORKFLOW.md §9 Git Cleanup | ~130 lines | Remove | Move to docs/history/ |

**Estimated savings**: ~500-600 lines trimmed from product docs.

### Move to `docs/design/` Candidates

| File | From | Rationale |
|------|------|-----------|
| `REPO_FLEET_MODE.md` | Root | Future design (v0.5+) — not current product |
| SPEC.md §13 Fleet Mode content | SPEC.md | Future design detail |
| SPEC.md §14 Agency Update content | SPEC.md | Future / v0.2+ design detail |
| SPEC.md §15 Contract Schemas (full YAML) | SPEC.md | Full schema examples belong in design docs |

### Move to `docs/history/` Candidates

| File | From | Rationale |
|------|------|-----------|
| `GIT_PLAN.md` | Root | Historical bootstrap planning |
| `GITHUB_SETUP_PLAN.md` | Root | Historical setup instructions |
| `PATCH_PLAN.md` | Root | Historical patch plan (code review followup) |
| `REVIEW_REPORT.md` | Root | Historical code review |
| `TEST_RESULTS.md` | Root | Historical test snapshot |
| `RESEARCH_NOTES.md` | Root | Historical research |
| WORKFLOW.md §9 | WORKFLOW.md | Historical bootstrap instructions |

### Not Moved (Stay at Root)

| File | Rationale |
|------|-----------|
| `README.md` | Entry point — must be at root |
| `ROADMAP.md` | Core product doc — must be at root |
| `ARCHITECTURE.md` | Core product doc — must be at root |
| `SPEC.md` | Core product doc — must be at root (compressed) |
| `DESIGN_FOUNDATIONS.md` | Core reference — stay at root |
| `WORKFLOW.md` (sections 1-8) | Contributor guide — stay at root |

---

## 5. Cross-Document Consistency Fixes

### Terminology

| Concept | Current Best Term | Inconsistent Uses | Fix |
|---------|-------------------|-------------------|-----|
| Three pillars | Role / Boundary / Completion | None remaining | ✅ Already aligned |
| Safe-defaults count | 21 checks (20 pass + 1 skip) | "21 safe-default rules" (README) vs "20+ checks" (ROADMAP) | Align to "21 checks" everywhere |
| CLI command prefix | `hermes-fleet` | Consistent | ✅ |
| Validator name | `test safe-defaults` | Consistent | ✅ |

### CLI Command Consistency

| Command | README | ARCHITECTURE | SPEC | ROADMAP | Actual |
|---------|--------|--------------|------|---------|--------|
| `init` | ✅ | ✅ | ✅ | ✅ | ✅ |
| `plan "<goal>"` | ✅ | ✅ | ✅ | ✅ | ✅ |
| `generate` | ✅ | ✅ | ✅ | ✅ | ✅ |
| `test safe-defaults` | ✅ | ✅ | ✅ | ✅ | ✅ |

All consistent. No discrepancies found.

### Version Scope Consistency

| Feature | README | ARCHITECTURE | SPEC | ROADMAP |
|---------|--------|--------------|------|---------|
| v0.1 = generator + validator | ✅ Clear | ✅ Clear | ✅ Clear | ✅ Clear |
| v0.2 = contracts + agency-agents | ✅ Clear | ✅ Mentioned | ⚠️ Mixed with current | ✅ Clear |
| v0.3 = container lifecycle | ✅ Clear | ✅ Clear | ✅ Clear | ✅ Clear |
| v0.5+ = Fleet Mode | ⚠️ Not mentioned | ✅ Detailed | ✅ Detailed | ✅ Detailed |

### Safe-Defaults Count Consistency

| Doc | Expression | Actual Count | Match? |
|-----|-----------|-------------|--------|
| README.md | "21 safe-default rules" | 20 pass + 1 skip | ⚠️ In context it says "Validate generated config against 21 safe-default rules" near a table — acceptable |
| ARCHITECTURE.md | "21 safe-defaults checks" in header | 20 + 1 | ✅ Acceptable |
| SPEC.md | "21 safe-defaults checks" in §9 | 20 + 1 | ✅ Acceptable |
| CODE | `safe_defaults.py` | 21 check functions | ✅ |

The 21st check is `check_kanban_templates_generated` which triggers a skip
if Docker Compose only has 1 service (and thus no multi-agent kanban needed).
The count is technically correct: 21 checks defined, with dynamic pass/skip
based on team size.

---

## 6. Recommended Cleanup PR

### Files to Change

```
Modify:
├── README.md               — Minor: combine What-v0.1-Does + What-This-Project-Is
├── ROADMAP.md              — Compress v0.5+ into brief "Future" section
├── ARCHITECTURE.md         — Compress §Contract Architecture, §Fleet Mode, §Agency-Agents
├── SPEC.md                 — Remove/move §13 Fleet Mode, §14 Agency, compress §15 Contracts
├── WORKFLOW.md             — Remove §9 Git Cleanup (move to docs/history/)

Move (git mv):
├── GIT_PLAN.md             → docs/history/GIT_PLAN.md
├── GITHUB_SETUP_PLAN.md    → docs/history/GITHUB_SETUP_PLAN.md
├── PATCH_PLAN.md           → docs/history/PATCH_PLAN.md
├── REVIEW_REPORT.md        → docs/history/REVIEW_REPORT.md
├── TEST_RESULTS.md         → docs/history/TEST_RESULTS.md
├── RESEARCH_NOTES.md       → docs/history/RESEARCH_NOTES.md
├── REPO_FLEET_MODE.md      → docs/design/REPO_FLEET_MODE.md

Not moved:
├── DESIGN_FOUNDATIONS.md   — No changes needed
├── .gitignore              — No changes needed
├── pyproject.toml          — No changes needed
├── src/                    — No changes (code is never touched)
├── tests/                  — No changes
├── presets/                — No changes
```

### Estimated Impact

| Metric | Before | After | Reduction |
|--------|--------|-------|-----------|
| Root .md files | 16 | 7 (READMe, ROADMAP, ARCHITECTURE, SPEC, DESIGN_FOUNDATIONS, WORKFLOW, CLEANUP_PLAN) | -56% |
| Product doc lines | ~2,000 | ~1,500 | -25% |
| Historical lines at root | ~1,189 | 0 | -100% |
| Future design at root | 2 (AAP + Fleet Mode) | 0 | ✅ moved |

### Verification Commands

```bash
# 1. All moves are correct
git status --short           # expect: moved files + modified .md files

# 2. No code/test/preset changes
git diff --name-only | grep -v '\.md$' | grep -v '^docs/'
# Expect: no output

# 3. Tests still pass
python -m pytest tests/ -q
# Expect: 173 passed

# 4. No stale references
grep -r "GIT_PLAN.md\|GITHUB_SETUP_PLAN.md\|PATCH_PLAN.md\|REVIEW_REPORT.md\|TEST_RESULTS.md\|RESEARCH_NOTES.md" \
  --include='*.md' README.md ROADMAP.md ARCHITECTURE.md SPEC.md DESIGN_FOUNDATIONS.md WORKFLOW.md
# Expect: no cross-references to moved historical docs

# 5. REPO_FLEET_MODE.md references still resolve
grep -r "REPO_FLEET_MODE" --include='*.md' .
# Expect: updated paths to docs/design/REPO_FLEET_MODE.md
```

### Expected Commit Messages

```
# Commit 1: Move historical docs to docs/history/
git mv GIT_PLAN.md GITHUB_SETUP_PLAN.md PATCH_PLAN.md REVIEW_REPORT.md \
       TEST_RESULTS.md RESEARCH_NOTES.md docs/history/
git commit -m "docs: archive historical bootstrap and review artifacts to docs/history/"

# Commit 2: Move future design docs to docs/design/
git mv REPO_FLEET_MODE.md docs/design/
git commit -m "docs: move Fleet Mode future design to docs/design/"

# Commit 3: Compress product docs
git add -p README.md ROADMAP.md ARCHITECTURE.md SPEC.md WORKFLOW.md
git commit -m "docs: compress speculative future sections, trim ARCHITECTURE and SPEC"
```

Or, if single-intent commit is preferred:

```
git commit -m "docs: archive historical artifacts, move future designs, compress product docs

- Move 6 bootstrap/review artifacts to docs/history/
- Move REPO_FLEET_MODE.md to docs/design/
- Compress SPEC.md Speculative Section (Fleet Mode, Agency Update, Contract Schemas)
- Compress ARCHITECTURE.md (Contract Architecture, Fleet Mode sections)
- Compress ROADMAP.md v0.5+ into brief Future section
- Remove WORKFLOW.md §9 (Git Cleanup Plan)
- Minor README.md consolidation

Total root .md files: 16 → 7. Product doc lines: ~2,000 → ~1,500.
No code, test, preset, or generator changes.
173 tests pass."
```

### Risk Level

| Risk | Mitigation |
|------|-----------|
| External links to moved docs break | Only GITHUB_SETUP_PLAN.md and GIT_PLAN.md are referenced by other docs — update those cross-references |
| User disagrees with cuts | Each change is additive to docs/design/ + docs/history/ — nothing is deleted, only moved or compressed. Easy to revert. |
| YAML contract schemas needed for reference | Full schemas remain in SPEC.md or docs/design/ — nothing lost |
| AAP doc reference breaks | AAP at docs/design/AGENT_ACCOUNTABILITY_PROTOCOL.md — already correct path |

**Overall risk**: Low. No deletions, only moves and compressions. All content
preserved in `docs/` subdirectories.

---

## 7. Automation Opportunities

> These are ideas to consider for future versions. **Do not implement now.**

### 7.1 `hermes-fleet check` (or `verify`)

A single command that runs the full validation suite:
```bash
hermes-fleet check        # runs safe-defaults + structure + cross-ref checks
hermes-fleet check --full # everything including deterministic tests
```
Currently users run `hermes-fleet test safe-defaults`. A shorter `check` alias
could be added in v0.2.

### 7.2 `hermes-fleet doctor`

A diagnostic command that checks:
- Is `.fleet/fleet.yaml` valid?
- Are all referenced role presets present?
- Is the generated output consistent with the current team?
- Are there any stale generated files?

This is a convenience wrapper around existing validator checks.

### 7.3 PR Template Generation

Auto-generate a GitHub PR template from the team's handoff contracts:
```bash
hermes-fleet pr-template > .github/PULL_REQUEST_TEMPLATE.md
```
Useful for Fleet Mode but not needed in v0.1/v0.2.

### 7.4 Documentation Health Check

A script that verifies:
- All cross-references between docs resolve
- CLI commands mentioned in docs match actual CLI
- Safe-defaults count is consistent across docs
- Version scope boundaries are respected

Could be a CI step in v0.3+.

---

## Summary

| Item | Count |
|------|-------|
| Root docs to move to `docs/history/` | 6 files (~1,189 lines) |
| Root future design to move to `docs/design/` | 1 file (~278 lines) |
| Product docs to compress | 5 files (~500 lines savings) |
| Root files after cleanup | 7 (.md) + 2 (infra) = 9 total |
| Code/test/preset/generator changes | 0 |
| Risk | Low |
