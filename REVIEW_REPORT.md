# Hermes Fleet v0.1 — Code Review Report

**Reviewer**: Hermes Agent (independent reviewer mode)
**Scope**: v0.1 MVP — generator and validator only
**Status**: Code not modified during review

---

## Executive Summary

The v0.1 MVP is functionally complete and tests pass (76/76). The architecture is clean and well-separated into layers. Most issues found are non-critical — improvements in test quality, unused dependencies, and documentation gaps. **One medium-priority issue** (unused Jinja2 templates) representing architectural drift from the design docs.

---

## Medium Priority

### M1. Jinja2 templates directory is unused

**File**: `templates/*.j2` (6 files), `pyproject.toml` (jinja2 dependency)
**Severity**: Medium

The `templates/` directory contains 6 well-structured Jinja2 templates (SOUL.md.j2, policy.yaml.j2, docker-compose.yaml.j2, kanban-task.md.j2, handoff.md.j2, completion-gate.yaml.j2), but **none are used at runtime**. The actual rendering is done in two places:

- `generator.py:_render_soul_md()` — Python f-string interpolation (135 lines of inline template)
- `kanban.py` — Hardcoded string templates

The Jinja2 library (`jinja2>=3.1.0`) is listed as a dependency in `pyproject.toml` but never imported anywhere in `src/`.

**Impact**: Confusing for future contributors. The SPEC.md describes Jinja2 as the template engine, but the code doesn't use it. Adding Jinja2 at this stage would increase complexity unnecessarily since the existing f-string approach works well for 3 simple templates.

**Suggestion**: Either:
- (a) Wire up Jinja2: load templates from `templates/` directory in `generator.py` and render with Jinja2 instead of f-strings → removes `_render_soul_md()`, uses `templates/SOUL.md.j2`, `templates/policy.yaml.j2`, etc.
- (b) Remove Jinja2: delete `templates/` directory, remove jinja2 from pyproject.toml dependencies, update SPEC.md to reflect f-string approach

Either is acceptable. (b) is simpler for v0.1 scope.

---

## Low Priority — Minor Issues

### L1. Test `test_default_output_is_not_verbose` doesn't actually test anything

**File**: `tests/test_safe_defaults.py` line 125-129
**Severity**: Low

```python
def test_default_output_is_not_verbose(self, generated_dir):
    results = run_safe_defaults_check(generated_dir, verbose=False)
    passing_in_results = [r for r in results if r["status"] == "passed"]
    for r in results:
        assert r["status"] != "passed" or r in results  # always True!
```

The assertion `r in results` is always True because `r` is an element of `results`. The comment says "passing checks shouldn't be in the returned list" but the assertion doesn't verify this. When `verbose=False`, the code at `safe_defaults.py:327` filters: `if verbose or r["status"] == "failed"` — so passing results are NOT added to the returned list. The test setup always creates passing results so the list should be empty, but the assertion never fails.

**Suggestion**: Replace with a meaningful assertion:
```python
assert all(r["status"] == "failed" for r in results), \
    "Non-verbose mode should only return failures"
```

### L2. Unused imports in source modules

**File**: Multiple
**Severity**: Low

| File | Unused Import |
|------|--------------|
| `safe_defaults.py:6` | `re` (never used) |
| `safe_defaults.py:8` | `Dict` (only `List` is used) |
| `docker_compose.py:5` | `Any`, `List` (only `Dict` is used) |
| `cli.py:11` | `os` (never used) |
| `cli.py:97` | `yaml` imported locally, but also never used in `plan()` |
| `cli.py:12` | `sys` (never used) |

Also: `cli.py` imports `yaml` both at module level (line 11... wait, no, actually it only imports inside functions. Let me recheck — lines 67 and 97 have `import yaml` inside function bodies).

Actually looking more carefully:
- `cli.py` line 67: `import yaml` inside `init()` — used  
- `cli.py` line 97: `import yaml` inside `plan()` — **NOT used** (the function never calls yaml.dump or yaml.safe_load)

**Suggestion**: Remove unused imports. Minimal but keeps the codebase clean.

### L3. `cli.py` has a local `_load_role()` that duplicates `teams.load_role()`

**File**: `cli.py:150-159` vs `teams.py:19-23`
**Severity**: Low

There are two separate functions that load role YAML from the same `presets/roles/` directory:
- `cli.py:_load_role()` — direct path resolution, returns empty dict on missing
- `teams.py:load_role()` — same logic, returns None on missing

The duplication is small (~6 lines) but means changes to role loading behavior must be made in two places.

**Suggestion**: Make `cli.py:_load_role()` delegate to `teams.load_role()`:
```python
def _load_role(role_id: str) -> dict:
    from hermes_fleet.teams import load_role
    role = load_role(role_id)
    return role if role else {"name": role_id.replace("-", " ").title()}
```

### L4. `hermes-fleet plan` doesn't persist the team selection

**File**: `cli.py:89-147`
**Severity**: Low (UX gap)

After `hermes-fleet plan "Build a SaaS"` recommends `saas-medium`, the user must manually edit `.fleet/fleet.yaml` to change the team from `general-dev` to `saas-medium`, or pass `--team saas-medium` during `generate`. Neither is obvious from the CLI output.

The `plan` command prints the recommendation but never writes to `fleet.yaml`.

**Suggestion**: Add an `--apply` flag to `plan` that updates `fleet.yaml`:
```python
hermes-fleet plan "Build a SaaS" --apply
```
This would update `.fleet/fleet.yaml` with the recommended team, so the subsequent `hermes-fleet generate` uses it automatically.

### L5. `safe_defaults.py` — `no_real_secrets_in_output` check is weak

**File**: `safe_defaults.py:287-296`
**Severity**: Low

The check only verifies that no `secrets/` directory was generated. It doesn't scan generated `policy.yaml` files for suspicious secret-like values in the allowlists. Currently the frontend-developer preset has `PUBLIC_STRIPE_KEY` in the allowlist — this is a legitimate dev key, but there's no automated check that secret names are actually safe.

**Suggestion**: Add a pattern-based check that scans all `policy.yaml` files for secret names containing words like `PROD`, `SECRET` (not `PUBLIC_SECRET`), `PASSWORD`, `TOKEN` in the `secrets.allow` list.

### L6. `SPEC.md` mentions Python >=3.11 but pyproject.toml uses >=3.10

**File**: `SPEC.md` line 454
**Severity**: Low

SPEC.md section 10 says `Python 3.11+` but `pyproject.toml` was changed to `>=3.10` for compatibility with the current environment. These should be consistent after the fix on line 454 was already patched — verify the SPEC.md now shows 3.10+.

---

## Cosmetic / Nitpicks

### C1. `generate_docker_compose()` uses `version: "3.8"` — should be Compose Specification format

Docker has deprecated `version:` in Compose files (Compose Specification v2). Modern Docker Compose ignores the version field. This is not a functional issue but could cause warnings.

### C2. Container image `nousresearch/hermes-agent:latest` may not exist

**File**: `docker_compose.py:49`
This is a placeholder image. If it doesn't exist on Docker Hub, `docker compose up` will fail. Consider documenting this as a placeholder or using a well-known base image.

### C3. Debug print statements in `_write_if_not_exists`

**File**: `generator.py:231,234`
The print() statements are useful CLI feedback but mean the module has side effects when imported. In library/test contexts, these prints go to stdout.

---

## Positive Findings

### P1. Well-structured layered architecture
The module separation (schema → planner → policy → generator → docker_compose → kanban → safe_defaults → cli) follows the architecture doc faithfully. Each module has a single responsibility.

### P2. Comprehensive safe-defaults validator
21 checks covering Docker security (cap_drop, no-new-privileges, pids_limit, read_only, no docker.sock, no host network), policy correctness (reviewer read-only, security-reviewer no-network, orchestrator no app code write, deployer disabled), and isolation (no ~/.hermes, no real secrets).

### P3. Test coverage is strong
76 tests cover team presets, SOUL.md generation (11 section tests), policy generation (10 tests), Docker Compose security (12 tests), safe-defaults validator (8 tests), Kanban templates (7 tests), planner (8 tests), and end-to-end (7 parametrized tests).

### P4. All v0.1 scope constraints respected
No Docker execution, no Hermes agent execution, no ~/.hermes access, no real secrets, no API keys needed, no existing profile dependency. The safe-defaults validator includes explicit isolation checks.

### P5. Deterministic output verified
End-to-end tests confirm that identical inputs produce identical file contents across separate runs.

---

## Summary

| Category | Count |
|----------|-------|
| Medium | 1 (M1: unused Jinja2) |
| Low | 5 (L1-L6) |
| Cosmetic | 3 (C1-C3) |
| Positive | 5 (P1-P5) |

**Verdict**: v0.1 MVP is functionally sound. The architectural drift between planned Jinja2 templates and actual f-string rendering (M1) is the main thing worth resolving before calling v0.1 complete. The remaining items are minor polish.
