# Prune Plan — v0.2 Post-Completion

**철학**: "단순한 칼이 가장 치명적이다" — v0.2 기능은 모두 완료했지만, 그 과정에서 생긴 죽은 코드와 중복 문서를 정리한다.

## 1. 측정 (Audit)

| 영역 | 라인 | 비고 |
|---|---|---|
| 소스 코드 | 2,893 | 11개 파일 |
| 문서 | 2,725 | 8개 파일 (+ .pytest_cache 제외) |
| 테스트 | 1,993 | 13개 파일 |
| YAML 프리셋 | 1,112 | 34개 파일 |

문서:코드 비율 = 0.94:1 — 여전히 높음.

## 2. 제거 후보 (CUT)

### CUT-1: `load_role_raw()` — 죽은 함수
- **파일**: `src/hermes_fleet/teams.py` line 66-78
- **사유**: 정의만 있고 `src/`와 `tests/` 전체에서 단 한 번도 호출되지 않음
- **크기**: 13줄
- **위험도**: 제거 후 테스트 영향 0 (grep으로 호출처 0건 확인)

### CUT-2: `generate_kanban_task()`, `generate_handoff_note()`, `generate_completion_gates()` — 죽은 내보내기
- **파일**: `src/hermes_fleet/kanban.py` lines 21-33
- **사유**: 3개 함수 모두 정의만 있고 import/호출처가 없음. `generate_kanban_templates()`만 사용됨
- **크기**: 12줄
- **위험도**: 제거 후 테스트 영향 0

### CUT-3: `kanban.py` `policy` 파라미터 — 죽은 파라미터
- **파일**: `src/hermes_fleet/kanban.py` — `generate_kanban_templates(policy=None)`
- **사유**: 호출자(`generator.py:72`)가 항상 `generate_kanban_templates()`로 인자 없이 호출. 내부 `_render_*` 함수들도 `if policy else []`에서 항상 빈 리스트로 fallback
- **크기**: 파라미터 타입 시그니처 4곳 + 조건부 로직
- **위험도**: `policy` 파라미터 제거 + 조건문 단순화. 기존 동작과 100% 동일

### CUT-4: `docs/AGENCY_AGENTS_UPDATE_MODEL.md` — 중복 문서
- **파일**: `docs/AGENCY_AGENTS_UPDATE_MODEL.md` (61줄, 3개 표 포함)
- **사유**:
  1. SPEC.md section 14와 내용 중복 (agency-agents update model)
  2. CLI가 "Future"로 기술되어 있으나 v0.2에서 이미 구현 완료
  3. **3개 표 포함** — 사용자가 표를 강하게 싫어함
  4. SPEC.md section 14에서만 참조됨 (1곳)
- **크기**: 61줄
- **위험도**: SPEC.md에서 참조 제거 후 삭제 가능

## 3. 최적화 후보 (OPTIMIZE)

### OPT-1: `kanban.py` 내부 단순화
- `_render_task_template(None)`, `_render_handoff_template(None)`, `_render_completion_gates(None)` 호출이 항상 동일한 템플릿을 반환
- `policy` 파라미터 제거 후 모든 `if policy:` 조건을 제거하고 고정 템플릿으로 단순화
- **효과**: 조건부 분기 4개 제거, 코드 가독성 향상

## 4. 유지 (KEEP)

| 항목 | 사유 |
|---|---|
| `SPEC.md` | 이미 표 없음, v0.2 반영 완료 |
| `ARCHITECTURE.md` | 이미 이전 pruning에서 Fleet Mode 제거됨 |
| `WORKFLOW.md` | 실제 프로세스 문서, v0.2 반영 필요 없음 |
| `DESIGN_FOUNDATIONS.md` | foundation.lock.yaml에서 참조 |
| `docs/design/REPO_FLEET_MODE.md` | 아카이브, ROADMAP에서 미래 참조 |
| 기존 테스트 | 모두 통과, 제거 불필요 |

## 5. 실행 계획

```
1. CUT-1: teams.py — load_role_raw() 제거
2. CUT-2: kanban.py — 3개 미사용 함수 제거
3. CUT-3: kanban.py — policy 파라미터 제거, 조건문 단순화
4. CUT-4: AGENCY_AGENTS_UPDATE_MODEL.md 삭제 + SPEC.md 참조 제거
5. VERIFY: pytest, hermes-fleet validate
```

## 6. 예상 효과

| 메트릭 | before | after | diff |
|---|---|---|---|
| 소스 코드 라인 | 2,893 | ~2,860 | -33 |
| 문서 라인 | 2,725 | ~2,664 | -61 |
| 테스트 통과 | 171 | 171 | 동일 |
| validate 체크 | 155 | 155 | 동일 |
