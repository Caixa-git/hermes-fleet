# Patch Plan — Hermes Fleet v0.1

> Plan only. No code changes yet.
> Based on REVIEW_REPORT.md findings.

---

## Decision Summary

| Issue | Severity | Decision | Rationale |
|-------|----------|----------|-----------|
| M1 | Medium | **Fix in v0.1** | Clean up architectural drift; remove unused Jinja2 |
| L1 | Low | **Fix in v0.1** | Test doesn't verify anything — must fix |
| L2 | Low | **Fix in v0.1** | Remove unused imports (polish) |
| L3 | Low | **Fix in v0.1** | Remove code duplication (polish) |
| L4 | Low | **Defer to v0.2** | New UX surface; scope creep risk; workaround exists (--team flag) |
| L5 | Low | **Fix in v0.1** (light) | Strengthen secret check with simple pattern scan |
| L6 | Low | **Fix in v0.1** | Already patched during review; verify consistency |
| C1 | Cosmetic | **Defer to v0.2** | No functional impact; Docker ignores version field |
| C2 | Cosmetic | **Defer to v0.2** | Placeholder image is expected in v0.1 (no Docker execution) |
| C3 | Cosmetic | **Won't fix** | Deliberate CLI feedback; not a bug |

---

## Must Fix Before v0.1

### 1. M1 — Remove unused Jinja2 templates and dependency

**Why**: 6 template files in `templates/` and `jinja2` in pyproject.toml are never used at runtime. All rendering is done via Python f-strings in `generator.py:_render_soul_md()` and hardcoded strings in `kanban.py`. This is architectural drift from the design docs.

**v0.1 scope**: Cleanup only. No new features, no behavior changes.

**Changes**:
1. Delete the entire `templates/` directory (6 files + directory)
2. Remove `"jinja2>=3.1.0"` from `pyproject.toml` dependencies list
3. Update `ARCHITECTURE.md` — section "4. Generator Layer" replaces "Rendered from `templates/*.j2`" with wording about Python f-string rendering
4. Update `SPEC.md` — section 10 "Technical Stack" removes Jinja2 row; section 4 "Generator Layer" updates template references; section 9 "Package Structure" removes `templates/` directory listing
5. Confirm all 76 tests still pass unchanged

**Files to change**:
- Delete: `templates/SOUL.md.j2`, `templates/policy.yaml.j2`, `templates/docker-compose.yaml.j2`, `templates/kanban-task.md.j2`, `templates/handoff.md.j2`, `templates/completion-gate.yaml.j2`, `templates/` (empty after)
- Modify: `pyproject.toml` (remove jinja2)
- Modify: `ARCHITECTURE.md` (update generator layer description)
- Modify: `SPEC.md` (update stack table, package structure, data flow)
- No change: `src/hermes_fleet/generator.py` (already works without Jinja2)
- No change: `src/hermes_fleet/kanban.py` (already works without Jinja2)

**Tests to run**: Full suite (`python -m pytest tests/ -q`). All 76 should pass.

---

### 2. L1 — Fix broken `test_default_output_is_not_verbose` assertion

**Why**: The test claims to verify that non-verbose mode only returns failed results, but its assertion `assert r["status"] != "passed" or r in results` is always True. This is a false-positive test.

**v0.1 scope**: Fix test correctness. No production code changes.

**Changes**:
1. In `tests/test_safe_defaults.py`, replace the weak assertion with:
   - Verify that when `verbose=False`, all returned results have `status == "failed"`
   - (Or verify that at least some passing results are NOT in the returned list)
   
   Best approach: generate a clean fixture, then verify that 0 passing results leak into non-verbose output.

**Files to change**:
- Modify: `tests/test_safe_defaults.py` (test `test_default_output_is_not_verbose`)

**Tests to run**: `python -m pytest tests/test_safe_defaults.py -v`

---

### 3. L2 — Remove unused imports

**Why**: Clean codebase. Imported but unused modules add noise and confuse static analyzers.

**v0.1 scope**: Import cleanup only. No behavior changes.

**Changes**:
1. `src/hermes_fleet/safe_defaults.py`:
   - Remove `import re` (line 6) — not used anywhere
   - Remove `Dict` from `from typing import ...` (line 8) — only `List` is used
2. `src/hermes_fleet/docker_compose.py`:
   - Remove `Any` from `from typing import ...` (line 5) — not used
   - Remove `List` from `from typing import ...` (line 5) — only `Dict` is used
3. `src/hermes_fleet/cli.py`:
   - Remove `import os` (line 11) — not used
   - Remove `import sys` (line 12) — not used
   - Remove unused `import yaml` inside `plan()` function (line 97) — not used

**Files to change**:
- Modify: `safe_defaults.py` (2 import lines)
- Modify: `docker_compose.py` (1 import line)
- Modify: `cli.py` (3 import lines)

**Tests to run**: Full suite + manual `hermes-fleet --help` smoke test.

---

### 4. L3 — Remove duplicate `_load_role` in cli.py

**Why**: `cli.py:_load_role()` and `teams.py:load_role()` do the same thing (read role YAML from presets/roles/). Duplicated code should be consolidated.

**v0.1 scope**: Refactor only. No behavior changes.

**Changes**:
1. In `cli.py:_load_role()` (line 150-159), replace the direct file read with a delegation call:
   ```python
   def _load_role(role_id: str) -> dict:
       from hermes_fleet.teams import load_role
       role = load_role(role_id)
       return role if role else {"name": role_id.replace("-", " ").title()}
   ```
2. Remove the `import yaml` inside `_load_role` (it becomes unused)
3. Remove the now-unnecessary direct path construction

**Files to change**:
- Modify: `cli.py` (simplify `_load_role` function body)

**Tests to run**: Full suite + manual `hermes-fleet plan "test" --show-details` smoke test.

---

### 5. L5 — Strengthen `no_real_secrets_in_output` validator check

**Why**: Current check only verifies no `secrets/` directory was generated. A better check scans generated `policy.yaml` files for suspicious secret names in the allowlists.

**v0.1 scope**: Strengthen existing validator check. No new commands, no new features.

**Changes**:
1. In `safe_defaults.py`, modify `no_real_secrets_in_output` check to also scan all generated `agents/*/policy.yaml` files:
   - Parse each `policy.yaml`
   - Check `secrets.allow` list for names containing: `PROD`, `PRODUCTION`, `SECRET` (not in `PUBLIC_*`), `PASSWORD`, `TOKEN`
   - If any found, return failed with agent name and offending secret name
   
   This is safe because:
   - It checks generated files only (not ~/.hermes)
   - It's pure YAML parsing (no network, no subprocess)
   - The production_secrets pattern list already exists at line 224-226

**Files to change**:
- Modify: `safe_defaults.py` (enhance `no_real_secrets_in_output` check function body)
- Possibly update: `tests/test_safe_defaults.py` (update test expectations if needed)

**Tests to run**: `python -m pytest tests/test_safe_defaults.py -v` + `cd examples/saas-medium && hermes-fleet test safe-defaults`

---

### 6. L6 — Verify SPEC.md Python version consistency

**Why**: SPEC.md section 10 says "Python 3.11+" but pyproject.toml uses ">=3.10". During review this was already patched in `SPEC.md` line 454. Just verify consistency.

**v0.1 scope**: Documentation consistency.

**Changes**:
1. Read SPEC.md section 10 to confirm `Python 3.10+` is present
2. If not, update it
3. Also check `README.md` and `ARCHITECTURE.md` for any Python version mentions

**Files to change** (if needed):
- Modify: `SPEC.md` (verify line 454 says 3.10+)
- Possibly: `README.md` if it mentions Python version

**Tests to run**: None needed (pure documentation).

---

## Optional v0.1 Fixes

None recommended. L4 (plan --apply) is deferred. C1-C3 are deferred or won't-fix.

---

## Deferred to v0.2

| Issue | Item | Reason |
|-------|------|--------|
| L4 | `plan --apply` flag | CLI surface expansion; workaround exists (--team flag or manual fleet.yaml edit) |
| C1 | Remove `version: "3.8"` from Compose output | Cosmetic; Docker ignores version field |
| C2 | Replace placeholder image | v0.1 doesn't run Docker; no need for real image |

---

## Files to Change (Summary)

| File | Action | Issue |
|------|--------|-------|
| `templates/` (directory) | **Delete** entire directory | M1 |
| `pyproject.toml` | Remove `"jinja2>=3.1.0"` from dependencies | M1 |
| `ARCHITECTURE.md` | Update generator layer description to remove Jinja2 references | M1 |
| `SPEC.md` | Update stack table, package structure, data flow to remove Jinja2 | M1 |
| `tests/test_safe_defaults.py` | Fix `test_default_output_is_not_verbose` assertion | L1 |
| `src/hermes_fleet/safe_defaults.py` | Remove `import re`, remove `Dict` from typing import; strengthen `no_real_secrets_in_output` | L2, L5 |
| `src/hermes_fleet/docker_compose.py` | Remove `Any`, `List` from typing import | L2 |
| `src/hermes_fleet/cli.py` | Remove `import os`, `import sys`, unused inner `import yaml`; simplify `_load_role` | L2, L3 |
| `tests/test_safe_defaults.py` | Update expectations if `no_real_secrets_in_output` behavior changes | L5 |

## Files NOT Changed

| File | Reason |
|------|--------|
| `src/hermes_fleet/generator.py` | Works correctly; Jinja2 removal is about deleting unused templates, not changing the renderer |
| `src/hermes_fleet/kanban.py` | Same as above |
| `src/hermes_fleet/planner.py` | No issues found |
| `src/hermes_fleet/teams.py` | No issues found |
| `src/hermes_fleet/schema.py` | No issues found |
| `src/hermes_fleet/policy.py` | No issues found |
| `RESEARCH_NOTES.md` | Research doc, not part of v0.1 delivery |
| `ROADMAP.md` | No changes needed |

---

## Tests to Run After All Patches

```bash
cd /workspace/hermes-fleet && python -m pytest tests/ -v
```

Expected result: 76 tests pass (or 77 if L5 adds a new test).

Also:
```bash
cd examples/general-dev && hermes-fleet generate --force && hermes-fleet test safe-defaults --verbose
cd examples/saas-medium && hermes-fleet generate --force && hermes-fleet test safe-defaults --verbose
hermes-fleet --help
```

---

## Completion Criteria

- [ ] All 76+ tests pass (no regressions)
- [ ] `templates/` directory removed
- [ ] Jinja2 removed from pyproject.toml
- [ ] `ARCHITECTURE.md` and `SPEC.md` updated (no Jinja2 references)
- [ ] `test_default_output_is_not_verbose` has a real assertion
- [ ] No unused imports remain in `safe_defaults.py`, `docker_compose.py`, `cli.py`
- [ ] `cli.py:_load_role` delegates to `teams.load_role()`
- [ ] `no_real_secrets_in_output` validator scans policy.yaml files
- [ ] SPEC.md Python version matches pyproject.toml (>=3.10)
- [ ] No changes touch `~/.hermes`, existing Hermes profiles, or `hermes-agent/venv`
- [ ] No Docker execution or Hermes agent execution
- [ ] Manual smoke test: `init → plan → generate → test safe-defaults` for both presets
