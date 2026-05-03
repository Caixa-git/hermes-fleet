# Git Plan — Hermes Fleet v0.1 Initial Setup

> This document plans the first Git initialization and commit.
> **Do not execute these commands yet.** This is the plan only.

---

## 1. Current Git Repository Status

| Check | Result |
|-------|--------|
| Git repo? | **No.** `fatal: not a git repository` |
| Branch | N/A |
| Working tree | N/A (no repo yet) |
| Git directory exists? | No `.git/` directory |

**Conclusion**: `git init` needs to be run first.

---

## 2. .gitignore Status

### Current `.gitignore`

```
# Hermes Fleet
__pycache__/
*.py[cod]
*.egg-info/
.pytest_cache/
.venv/
venv/
dist/
build/
*.egg
.fleet/generated/
```

### Coverage Analysis

| Category | Pattern | Status |
|----------|---------|--------|
| Python cache | `__pycache__/`, `*.py[cod]`, `.pytest_cache/` | Covered |
| Virtual environment | `.venv/`, `venv/` | Covered |
| Python build | `dist/`, `build/`, `*.egg`, `*.egg-info/` | Covered |
| Generated output | `.fleet/generated/` | Covered (matches `examples/*/.fleet/generated/` too) |
| OS files | `.DS_Store`, `Thumbs.db` | **Missing — add** |
| Secret files | `.env`, `.env.*`, `*.key`, `*secret*`, `*token*` | **Missing — add** |
| Large/binary | `*.zip`, `*.tar.gz`, `*.bin` | **Missing — add** |

### Recommended `.gitignore` Update

Add these patterns before `git init`:

```
# OS
.DS_Store
Thumbs.db

# Secrets
.env
.env.*
*.key
*secret*
*token*

# Large / binary
*.zip
*.tar.gz
*.bin
```

---

## 3. File Inventory

### Files That Should Be Tracked (75 files)

**Design docs (7):**
`README.md`, `ARCHITECTURE.md`, `ROADMAP.md`, `SPEC.md`, `DESIGN_FOUNDATIONS.md`, `WORKFLOW.md`, `RESEARCH_NOTES.md`

**Review artifacts (3, optional for v0.1):**
`REVIEW_REPORT.md`, `PATCH_PLAN.md`, `TEST_RESULTS.md`

**Configuration (1):**
`pyproject.toml`

**Source code (10):**
`src/hermes_fleet/__init__.py`, `cli.py`, `docker_compose.py`, `generator.py`, `kanban.py`, `planner.py`, `policy.py`, `safe_defaults.py`, `schema.py`, `teams.py`

**Presets (13):**
`presets/teams/general-dev.yaml`, `saas-medium.yaml`
`presets/roles/orchestrator.yaml`, `fullstack-developer.yaml`, `reviewer.yaml`, `qa-tester.yaml`, `technical-writer.yaml`, `product-manager.yaml`, `ux-designer.yaml`, `frontend-developer.yaml`, `backend-developer.yaml`, `database-architect.yaml`, `security-reviewer.yaml`

**Tests (9):**
`tests/__init__.py`, `test_team_presets.py`, `test_soul_generation.py`, `test_policy_generation.py`, `test_docker_compose_generation.py`, `test_safe_defaults.py`, `test_kanban_templates.py`, `test_planner.py`, `test_end_to_end.py`

**Example configs (2):**
`examples/general-dev/.fleet/fleet.yaml`, `examples/saas-medium/.fleet/fleet.yaml`

**Git infrastructure (1):**
`.gitignore`

**Total: ~46 core files** (review artifacts are optional).

### Files That Must NOT Be Tracked

| Path | Why | Ignored by |
|------|-----|-----------|
| `examples/*/.fleet/generated/` | Deterministic generator output | `.fleet/generated/` |
| `__pycache__/` anywhere | Python bytecode cache | `__pycache__/` |
| `.pytest_cache/` | Pytest cache | `.pytest_cache/` |
| `.venv/`, `venv/` | Virtual environments | `.venv/`, `venv/` |
| `*.egg-info/` | Package metadata | `*.egg-info/` |

### Review Artifacts Decision

| File | Track? | Reason |
|------|--------|--------|
| `REVIEW_REPORT.md` | Optional | Code review artifact. Useful for v0.1 history. |
| `PATCH_PLAN.md` | Optional | Patch planning doc. Historical value for v0.1. |
| `TEST_RESULTS.md` | Optional | Test run summary. Can be regenerated. |

**Recommendation**: Track all three. They document the v0.1 review and
patch process. Small files (3KB each), no maintenance burden.

---

## 4. Suspicious File Scan

| Scan | Result |
|------|--------|
| `.env` or `.env.*` files | **None found** |
| `*secret*`, `*token*`, `*.key` files | **None found** |
| `hermes-agent` references in file tree | **None found** |
| `~/.hermes` references in file tree | **None found** |
| Files over 500KB | **None found** |
| `.zip`, `.tar.gz`, `.bin` files | **None found** |

**Conclusion**: Clean. No suspicious files in the working tree.

---

## 5. First Commit Recommendation

### Decision: Option A — Single bootstrap commit

**Recommended.** Reason:

1. The project is a cohesive MVP — all files serve a single purpose
   (v0.1 generator/validator). There is no partial feature work in
   the tree.

2. The working tree is already in a stable, tested state (76 tests pass).
   There is no in-progress work that would benefit from split history.

3. Option B (layer-by-layer) adds ceremony without meaningful bisect
   value at this stage. The project has only one contributor and one
   session of development so far.

4. Subsequent work WILL follow small-commit discipline (WORKFLOW.md
   sections 1-8). The bootstrap commit is the only large commit.

### Rejected: Option B — Layer-by-layer

Rejected because:

- Splitting 46 files into 6-7 commits adds no practical value for a
  single-contributor bootstrap.
- The Jinja2 templates no longer exist, making the "feat: add templates"
  commit impossible to reconstruct cleanly.
- The source code modules (`src/`) and tests (`tests/`) are tightly
  coupled — separating them into different commits creates a window
  where tests reference nonexistent code.

---

## 6. Recommended Branch

| Recommendation | Value |
|----------------|-------|
| **Branch name** | `main` |
| **Remote** | `origin` — to be decided (see `GITHUB_SETUP_PLAN.md`).<br>HTTPS candidate: `https://github.com/Caixa-git/hermes-fleet.git`<br>SSH candidate: `git@github.com:Caixa-git/hermes-fleet.git` |

The first commit goes to `main`. Future feature work uses `feat/*`,
`docs/*`, `chore/*` branches per WORKFLOW.md section 2.

**Remote is NOT added in this phase.** Remote setup requires user
approval after GitHub repository creation.

---

## 7. Recommended Commit Message

```
chore: bootstrap hermes-fleet v0.1 MVP

A secure team bootstrapper for isolated Hermes Agent fleets.
v0.1 is a generator and validator — generates SOUL.md, policy.yaml,
Docker Compose, and Kanban templates from team presets.

Includes:
- CLI: init, plan, generate, test safe-defaults
- Team presets: general-dev, saas-medium
- Role presets: 11 role definitions with permission presets
- Generators: SOUL.md, policy.yaml, docker-compose, kanban
- Validator: 21 safe-defaults checks
- Tests: 76 passing tests across 8 test files
- Docs: design documents, workflow guide, research notes
```

---

## 8. Pre-Push Verification

Before `git remote add` and `git push`, run:

```bash
# 1. Verify clean status
git status --short
# Expect: nothing (working tree clean after commit)

# 2. Verify tracked files
git ls-files | head -50
# Look for: no .env, no secrets, no hermes-agent files

# 3. Review commit log
git log --oneline
# Expect: exactly one commit

# 4. Verify .gitignore coverage
cat .gitignore
# Confirm all patterns from section 2 above are present

# 5. Final secret scan
git ls-files | grep -E '\.env|secret|token|key|credential'
# Expect: no output

# 6. Final scope scan
git ls-files | grep -E 'hermes-agent|\.hermes'
# Expect: no output
```

---

## 9. Execution Order (When Approved)

```bash
# Step 1: Initialize repository
cd /workspace/hermes-fleet
git init

# Step 2: Verify .gitignore is complete
# (If patterns from section 2 are missing, add them first)

# Step 3: Stage all files
git add .

# Step 4: Verify staged content
git status --short
git diff --cached --stat

# Step 5: Verify no unwanted files are staged
git diff --cached --name-only | grep -E '\.env|secret|token|key|credential|hermes-agent|\.hermes'
# Must produce no output

# Step 6: Commit
git commit -m "chore: bootstrap hermes-fleet v0.1 MVP"

# --- User approval gate for remote ---

# Step 7: Add remote (after user approval — see GITHUB_SETUP_PLAN.md)
# git remote add origin https://github.com/Caixa-git/hermes-fleet.git

# Step 8: Push (after user approval)
# git push -u origin main
```

---

## 10. Summary

| Item | Value |
|------|-------|
| Git repo? | No — needs `git init` |
| Files to track | ~46 core files + 3 optional review artifacts |
| Suspicious files | None |
| .gitignore | Exists but needs OS/secret/binary patterns |
| First commit | **Option A** — single bootstrap commit |
| Branch | `main` |
| Commit message | `chore: bootstrap hermes-fleet v0.1 MVP` |
| Remote URL | `https://github.com/NousResearch/hermes-fleet.git` |
| Remote approval required? | Yes — user must approve before push |
