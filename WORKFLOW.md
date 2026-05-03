# Hermes Fleet — Workflow Guide

> Operating principles for Git workflow, deterministic testing,
> and the standard work loop. This document is the team's shared
> understanding of how to work on hermes-fleet safely.

---

## 1. Git Operating Principles

### 1.1 Core Rules

1. **Commit in small, testable units.** A single file with a meaningful
   change and passing tests is worthy of a commit. You do not need
   multiple files to justify a commit.

2. **Unify by intent, not by file count.** Multiple files that share
   the same purpose (e.g., "add foundation lock schema to schema.py
   and update its test") belong in one commit. Multiple files with
   unrelated purposes never belong in the same commit.

3. **Separate concerns.** Documentation changes, code changes, and
   test changes belong in separate commits when they can stand alone.
   If a code change requires a test change to be meaningful, they can
   be in the same commit.

4. **Check before committing.** Always run before every commit:

   ```bash
   git status --short          # see what's staged and unstaged
   git diff --stat             # review unstaged changes
   git diff --cached --stat    # review staged changes
   ```

5. **Guard against leaks.** Before `git commit`, verify:
   - No `.env`, `.env.*`, `*.key`, `*secret*`, `*token*` files are staged
   - No `__pycache__/`, `*.pyc`, `*.pyo`, `.pytest_cache/` are staged
   - No `*.zip`, `*.tar.gz`, `*.bin`, or large binary files are staged
   - No `venv/`, `.venv/` directories are staged
   - No files from `/workspace/hermes-agent/`, `/workspace/hermes-agent/venv/`,
     or `~/.hermes/` are anywhere near the staging area

### 1.2 Scope Boundary

- **Never** stage, track, or reference files from:
  - `/workspace/hermes-agent/` — the existing Hermes installation
  - `/workspace/hermes-agent/venv/` — the existing Hermes venv
  - `~/.hermes/` — the user's Hermes home directory
- All Git operations are limited to `/workspace/hermes-fleet/`.

---

## 2. Branch Strategy

### 2.1 Recommended Branches

| Branch | Purpose | Base |
|--------|---------|------|
| `main` | Stable v0.1 baseline | — |
| `chore/bootstrap-v0.1` | Current MVP cleanup and stabilization | `main` |
| `docs/*` | Documentation-only changes | `main` or `chore/bootstrap-v0.1` |
| `feat/*` | New feature branches | `main` or `chore/bootstrap-v0.1` |
| `fix/*` | Bug fixes | `main` or `chore/bootstrap-v0.1` |

### 2.2 Rules

- Do not commit new features directly to `main` during v0.1 stabilization.
- Use `chore/bootstrap-v0.1` for cleanup, polish, and documentation.
- Separate documentation changes into `docs/` branches when they are
  large enough to warrant isolation.
- Feature implementation goes into `feat/` branches.
- Merge back to `main` only after review and full test suite pass.

---

## 3. Commit Strategy

### 3.1 Message Format

```
<type>: <brief description of intent>
```

| Type | When |
|------|------|
| `docs` | Documentation only (README, ARCHITECTURE, SPEC, DESIGN_FOUNDATIONS, WORKFLOW) |
| `feat` | New capability in src/hermes_fleet/ |
| `test` | New or updated tests |
| `fix` | Bug fix or incorrect behavior correction |
| `chore` | Bootstrap, infra, CI, dependency changes |
| `refactor` | Code restructuring with no behavior change |

### 3.2 Examples

```
docs: define design foundations and onboarding protocol
feat: generate role policies from team presets
test: add safe-defaults validator coverage
fix: remove unused jinja dependency
chore: bootstrap hermes-fleet v0.1 MVP
refactor: split safe-default checks into reusable functions
```

### 3.3 Pre-Commit Checklist

```text
[ ] git status --short — clean, intentional
[ ] git diff --cached --stat — staged files make sense together
[ ] No secret-like files in staging area
[ ] No hermes-agent files in staging area
[ ] No large binaries or caches in staging area
[ ] All related tests pass
[ ] Change scope matches a single intent
[ ] Commit message follows <type>: <description>
```

### 3.4 Suspicious File Check Commands

Before every commit, run one of these to catch secrets, caches, and
out-of-scope files that may have been staged accidentally:

```bash
# Check staged file names for suspicious patterns
git diff --cached --name-only | grep -E '\.env|secret|token|key|credential|venv|__pycache__|\.pyc|\.zip|\.bin' \
  && echo "⚠  Suspicious files staged — review before committing" \
  || echo "✓  No suspicious file names detected"

# Check staged file names for hermes-agent or home directory
git diff --cached --name-only | grep -E 'hermes-agent|\.hermes|home/' \
  && echo "⚠  Out-of-scope files staged — remove immediately" \
  || echo "✓  No out-of-scope files detected"

# Full working-tree scan for credential patterns (unstaged warning)
git ls-files --others --exclude-standard | grep -E '\.env$|\.env\.[a-zA-Z]+$|*secret*|*token*|*credential*' \
  && echo "⚠  Untracked suspicious files exist — add to .gitignore or delete" \
  || echo "✓  No untracked suspicious files"

# Check for large files in staged changes
git diff --cached --stat | awk -F'|' '{ if ($2+0 > 500) print $0 }' \
  && echo "⚠  Large files staged (>500 lines) — verify intent" \
  || echo "✓  No unusually large files staged"

# Guard: ensure .fleet/generated/ is never staged
git diff --cached --name-only | grep '\.fleet/generated/' \
  && echo "⚠  Generated output staged — add to .gitignore and unstage" \
  || echo "✓  No generated output staged"
```

These commands are informational. They do not block the commit. If they
flag a real issue, investigate before committing. If they produce a false
positive (e.g., a deliberate test fixture with "token" in its path), add
it to the allowlist in a local script and annotate the exception.

---

## 4. Deterministic Testing Principles

### 4.1 Core Rules

1. **Tests must be deterministic.** The same test input must always
   produce the same test output. No flakiness from network calls,
   random seeds, or external state.

2. **No real AI API calls in tests.** Any LLM-dependent functionality
   is tested with mocked responses or fixed fixtures. Real API calls
   are manual acceptance tests only.

3. **No real Docker execution in v0.1 tests.** Docker Compose output
   is validated structurally (YAML parsing, field assertions) but
   never executed. `.fleet/generated/docker-compose.generated.yaml`
   is a text artifact, not a runtime command.

4. **No real Hermes agent execution in v0.1 tests.** The generated
   SOUL.md, policy.yaml, and kanban templates are validated as
   documents, not as running agents.

5. **Test against generated files and schemas.** The primary test
   surface is:
   - Generated YAML and markdown files
   - Pydantic schema validation
   - Cross-reference integrity (role↔preset, handoff↔role)
   - Safety invariants (no privileged containers, etc.)
   - Deterministic allocation (same input → same output)

### 4.2 Determinism Guarantee

Given the same:
- `foundation.lock.yaml` version
- `agency.lock.yaml` ref
- Goal text or fixture input
- Mapping table

The same Team Proposal must be produced every time. The test suite
verifies this with **Deterministic Allocation Tests** that run the
full pipeline on fixed fixtures and assert byte-identical output.

---

## 5. Reusable Test Unit Design

### 5.1 Pattern

Each safety check or contract validation is a pure function that takes
structured data and returns a result. File I/O is handled by a loader
layer; validation functions never read files directly.

```python
# Pattern:
def check_<rule>(data: dict) -> CheckResult:
    ...
    return CheckResult(passed=True, message="...")
```

### 5.2 Examples

| Function | Input | Output |
|----------|-------|--------|
| `check_no_privileged_containers(compose)` | Docker Compose dict | CheckResult |
| `check_no_docker_sock_mount(compose)` | Docker Compose dict | CheckResult |
| `check_reviewer_readonly(policy, compose)` | policy dict, compose dict | CheckResult |
| `check_security_reviewer_no_network(policy, compose)` | policy dict, compose dict | CheckResult |
| `check_no_production_secrets(policies)` | list of policy dicts | CheckResult |
| `check_role_has_handoff_contract(role_contract)` | Role Contract dict | CheckResult |
| `check_team_roles_exist_in_inventory(team_contract, role_inventory)` | Team Contract, role list | CheckResult |
| `check_handoff_allowed_next_roles_exist(handoff_contract, role_inventory)` | Handoff Contract, role list | CheckResult |
| `check_team_proposal_matches_schema(proposal)` | Team Proposal dict | CheckResult |
| `check_capability_role_mapping_is_stable(input_fixture)` | fixture | CheckResult |

### 5.3 Rules

- File I/O belongs in a **loader layer** (e.g., `teams.py`, a future
  `contract_loader.py`), never in validation functions.
- Validation functions accept `dict`, `list`, or Pydantic models —
  never file paths.
- Each function returns a `CheckResult` with `passed: bool` and
  `message: str`.
- CLI commands call validation functions; they do not reimplement them.
- E2E tests are minimized. Most coverage comes from pure validation
  tests that call check functions directly.

---

## 6. Test Categories

### 6.1 Schema Tests

Validate that every contract definition conforms to its schema.

- Team Contract schema validation
- Role Contract schema validation
- Handoff Contract schema validation
- Team Proposal schema validation

### 6.2 Cross-Reference Tests

Validate that all references between contracts resolve correctly.

- Every `role_id` in a Team Contract's `role_inventory` exists
- Every `permission_preset` in a Role Contract exists in the preset inventory
- Every `handoff_contract` in a Role Contract exists in the handoff inventory
- Every `allowed_next_roles` entry in a Handoff Contract exists in the role inventory

### 6.3 Safety Invariant Tests

Validate hard safety rules that must never be violated under any valid
configuration.

- Deployer is disabled by default
- Production secrets are denied by default
- Reviewer workspace is read-only
- Security-reviewer has no network access
- Orchestrator cannot write application code
- No docker.sock mount in any service
- No privileged containers
- No host network mode

### 6.4 Deterministic Allocation Tests

Validate that the same inputs produce identical outputs every time.

- Fixture prompt → expected goal classification
- Fixture prompt → expected capability list
- Capability list → expected role list
- Role list → expected policy presets
- Role list → expected handoff contracts

### 6.5 Handoff Validation Tests

Validate that handoff contracts enforce their rules.

- Missing required fields → failure
- Missing `approval_or_block` → failure
- Severity enum mismatch → failure
- Next role outside `allowed_next_roles` → failure

### 6.6 Snapshot / Golden File Tests

Validate that generated output does not change unintentionally.

- Same preset generate → identical output across runs
- Generated SOUL.md / policy.yaml / docker-compose do not drift
  on unrelated changes

#### Golden File Change Protocol

When a golden snapshot file must be updated (because the generator
behavior intentionally changed):

1. **Record the reason.** The commit message or a companion comment
   must explain why the golden output changed. Examples:
   - "Added network_access field to security-reviewer policy"
   - "Updated orchestrator app-code guard to include patterns/"

2. **Review the diff.** Before committing the new golden file, run:
   ```bash
   git diff tests/fixtures/*.golden.yaml
   ```
   Verify every line change is intentional. If you see unexpected
   diffs (whitespace, ordering, timestamps), investigate before
   committing.

3. **Check lock layers.** Verify whether the change was caused by:
   - A `foundation.lock.yaml` or `agency.lock.yaml` update
   - A mapping table change
   - An unrelated generator drift (fix immediately)

4. **Rule out unrelated drift.** If the golden output changed but
   no intentional generator change was made, this is **drift** and
   must be investigated and fixed before any commit proceeds.

5. **One golden update per intent.** If multiple golden files change
   for unrelated reasons, split them into separate commits or verify
   they are all consequences of the same root cause.

### 6.7 CLI Smoke Tests

Validate that CLI commands run without errors.

- `hermes-fleet init`
- `hermes-fleet plan "<goal>"`
- `hermes-fleet generate`
- `hermes-fleet test safe-defaults`

---

## 7. Work Loop

The standard loop for every change:

```text
1. Define scope in one sentence.
   "I will add the handoff contract schema to SPEC.md."

2. Limit files to change.
   Only SPEC.md. No source code, no tests.

3. Select verification command.
   For docs: manual review.
   For code: python -m pytest tests/path/to/file.py -v
   For full: python -m pytest tests/ -q

4. Make the change.

5. Run verification.
   pytest passes or document reads correctly.

6. Review git diff.
   git diff --stat
   git diff           # or git diff --cached if staged

7. Guard check.
   No secrets. No caches. No hermes-agent files. No venv.

8. Create a small commit.
   git add <files>
   git commit -m "docs: add handoff contract schema"

9. Move to next work item.
```

---

## 8. When Not To Commit Immediately

Do not commit when any of these conditions are true:

| Condition | Action |
|-----------|--------|
| Tests are failing | Fix tests or revert the change |
| Multiple unrelated changes in staged files | Split into separate commits |
| Secret-like files appeared in working tree | Investigate, delete, update .gitignore |
| Generated output changed unexpectedly | Understand the diff before committing |
| Change exceeds v0.1 scope | File as a feature request, do not commit |
| `hermes-agent/` files appear in diff | Stop. These must never be in git context |
| `~/.hermes` references appear in new code | Remove the reference immediately |

---

## 9. Initial Git Cleanup Plan

> This section describes what to do when we first initialize the
> repository. Do not execute these steps yet — they are documented
> for the first Git setup session.

### 9.1 Check Status

```bash
cd /workspace/hermes-fleet
git status                     # is it a repo?
git rev-parse --is-inside-work-tree  # exits 0 if inside git repo
```

If not a repo yet:

```bash
git init
```

### 9.2 .gitignore Essentials

Ensure `.gitignore` contains:

```
# Python
__pycache__/
*.py[cod]
*.egg-info/
.pytest_cache/
.venv/
venv/

# Build
dist/
build/
*.egg

# Generated output (safe to regenerate)
.fleet/generated/

# Why .fleet/generated/ is ignored:
#   - hermes-fleet generate produces this directory deterministically.
#   - It is safely regenerated from presets/ + templates/ on every run.
#   - Committing it bloats the repository and creates merge conflicts
#     on every generate-diff cycle.
#   - If a specific generated output needs to be preserved as a golden
#     fixture, copy it to tests/fixtures/ or examples/ with an explicit
#     name and a comment explaining why it is tracked.
#
# Golden fixture exception:
#   tests/fixtures/*.golden.yaml     # explicit golden snapshots
#   examples/*/.fleet/generated/     # NOT tracked — examples regenerate

# Secrets
.env
.env.*
*.key
*secret*
*token*

# OS
.DS_Store
Thumbs.db

# Large / binary
*.zip
*.tar.gz
*.bin
```

### 9.3 First Commit Decision

**Option A — One mega-commit (simpler for v0.1 bootstrap):**

```bash
git add .
git commit -m "chore: bootstrap hermes-fleet v0.1 MVP"
```

Use this when the working tree is messy and splitting history is not
worth the effort for a bootstrap. The cost is a large initial commit
that cannot be bisected, but for a generator/validator MVP this is
acceptable.

**Option B — Split by layer (cleaner for bisect):**

```bash
git add README.md ARCHITECTURE.md ROADMAP.md SPEC.md RESEARCH_NOTES.md \
   DESIGN_FOUNDATIONS.md WORKFLOW.md
git commit -m "docs: add design documents and workflow guide for v0.1"

git add pyproject.toml src/
git commit -m "chore: add CLI skeleton and core modules"

git add presets/
git commit -m "feat: add team and role presets"

git add tests/
git commit -m "test: add test suite for v0.1"

git add examples/ .gitignore
git commit -m "chore: add example outputs and gitignore"
```

Split by functional layer. Note that `templates/` was present during
initial development but has been removed — the current renderer uses
Python f-strings directly. No `templates/` directory should be tracked.

`.fleet/generated/` is in `.gitignore` and must never be added.
If a golden fixture is needed, copy it to `tests/fixtures/` with a
`.golden.yaml` extension and add an explicit `!` exception in
`.gitignore` only for that specific file.

**Recommendation:** For the initial bootstrap, use Option A. The
current state is a working MVP, not an in-progress feature. Once the
first commit is made, all subsequent changes follow the small-commit
discipline defined in sections 1-8 above.

---

## 10. GitHub Remote and First Push Checklist

> Do not execute these steps until the user has explicitly approved
> the remote connection and push.

### 10.1 Repository Visibility Decision

Before adding a remote, decide:

| Visibility | When |
|------------|------|
| **Public** | Open-source project. Anyone can clone, fork, contribute. |
| **Private** | Internal or early-stage work. Only invited collaborators can see it. |

Default for hermes-fleet: **public** (it is an open-source project).

### 10.2 Pre-Push Verification

Run these checks before `git remote add` and `git push`:

```bash
# 1. Check working tree is clean
git status --short
# Must show nothing (or only intentional unstaged files)

# 2. Show tracked files
git ls-files
# Verify no unexpected files are being tracked. Look for:
#   - .env, .env.*, *secret*, *token*, *.key
#   - __pycache__/, *.pyc, .pytest_cache/
#   - .fleet/generated/  (must NOT be tracked)
#   - hermes-agent/ or ~/.hermes/ files (must NOT be tracked)

# 3. Verify .gitignore covers all ignore patterns
cat .gitignore
# Confirm .fleet/generated/, __pycache__/, .env, venv/ are present

# 4. Full working-tree scan for secret-like files (not just tracked)
git ls-files --others --exclude-standard | grep -E '\.env|secret|token|key|credential' \
  && echo "⚠  Untracked secret-like files exist — investigate" \
  || echo "✓  No secret-like untracked files"

# 5. Review commit log before push
git log --oneline
# Verify:
#   - No "WIP", "fix this", "temp" messages
#   - Each commit message follows <type>: <description>
#   - No commits that mix unrelated concerns

# 6. Final guard: confirm no hermes-agent files leaked
git ls-files | grep -E 'hermes-agent|\.hermes' \
  && echo "⚠  Out-of-scope files tracked — abort push" \
  || echo "✓  No out-of-scope files tracked"
```

### 10.3 Remote Setup

```bash
# Add remote (use the correct repository URL)
git remote add origin https://github.com/NousResearch/hermes-fleet.git

# Verify remote
git remote -v
```

### 10.4 First Push

```bash
git push -u origin main
```

### 10.5 Post-Push Verification

After the push completes:

1. Open the repository in a web browser.
2. Verify the file list shows only expected files:
   - `README.md`, `ARCHITECTURE.md`, `ROADMAP.md`, `SPEC.md`, etc.
   - `src/`, `presets/`, `tests/`, `examples/`
   - `.gitignore`, `pyproject.toml`
3. Verify no unexpected files are present:
   - No `.env`, no `*.secret`, no `*.token`
   - No `hermes-agent/` directory
   - No `.fleet/generated/` directory
   - No `__pycache__/` or `*.pyc`
4. If anything unexpected appears in the remote, investigate and
   fix locally before pushing again.

### 10.6 User Approval Gate

**No remote connection or push happens without explicit user approval.**
The approval must cover:
- Which remote URL
- Which branch to push
- Whether the repository is public or private
- Confirmation that the pre-push verification passed

---

## 11. Summary of Principles

| Area | Principle |
|------|-----------|
| **Commit size** | One intent per commit. A single-file change with passing tests is valid. |
| **Branch hygiene** | `main` is stable. `chore/`, `docs/`, `feat/`, `fix/` branches for active work. |
| **Deterministic testing** | No real AI, Docker, or Hermes execution in tests. Same input → same output. |
| **Pure validators** | Validation functions accept data, not paths. I/O is separate from logic. |
| **Guard before commit** | Check for secrets, caches, hermes-agent files, and scope creep before every commit. |
| **Work loop** | Define scope → limit files → verify → change → verify → diff → guard → commit → next. |
