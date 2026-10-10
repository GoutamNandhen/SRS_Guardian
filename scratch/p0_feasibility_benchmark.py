"""SRS Guardian Phase P0: synthetic incremental evidence invalidation experiment.

This is an isolated research feasibility test, NOT a patentability demonstration,
NOT an integration with the production NLP/ML system, and NOT an SMT benchmark.
Runs using only the Python standard library.

Assumption under test: constraints are correctly assigned to independent scopes.
Unknown cross-scope dependencies force a conservative full recomputation.
"""
from __future__ import annotations
from dataclasses import dataclass, replace
from collections import defaultdict
from statistics import median
from time import perf_counter
import random


@dataclass(frozen=True)
class Requirement:
    id: str
    scope: str
    operator: str  # >= or <=
    value: int
    text_revision: int = 0


@dataclass(frozen=True)
class Evidence:
    scope: str
    source_ids: tuple[str, ...]
    strongest_lower: int | None
    strongest_upper: int | None
    conflict: bool
    engine_version: str
    interpretation_version: str


def summarize_scope(scope: str, source_entries: list[Requirement],
                    engine_version: str, interpretation_version: str) -> Evidence:
    entries = sorted(source_entries, key=lambda r: r.id)
    lowers = [r.value for r in entries if r.operator == '>=']
    uppers = [r.value for r in entries if r.operator == '<=']
    lower = max(lowers) if lowers else None
    upper = min(uppers) if uppers else None
    return Evidence(scope, tuple(r.id for r in entries), lower, upper,
                    lower is not None and upper is not None and lower > upper,
                    engine_version, interpretation_version)


def all_scopes(reqs: dict[str, Requirement]) -> set[str]:
    return {r.scope for r in reqs.values()}


def verify_full(reqs: dict[str, Requirement], engine_version='v1',
                interpretation_version='v1') -> tuple[dict[str, Evidence], int]:
    grouped: dict[str, list[Requirement]] = defaultdict(list)
    for req in reqs.values():
        grouped[req.scope].append(req)
    return ({g: summarize_scope(g, grouped[g], engine_version, interpretation_version)
             for g in sorted(grouped)}, len(grouped))


def verify_incremental(old_reqs: dict[str, Requirement],
                       new_reqs: dict[str, Requirement],
                       old_evidence: dict[str, Evidence],
                       old_engine_version='v1', new_engine_version='v1',
                       old_interpretation_version='v1',
                       new_interpretation_version='v1',
                       cross_scope_dependencies_known=True
                       ) -> tuple[dict[str, Evidence], int]:
    # Conservative fallback: changed verification logic or unknown cross-scope links.
    if (old_engine_version != new_engine_version or
        old_interpretation_version != new_interpretation_version or
        not cross_scope_dependencies_known):
        return verify_full(new_reqs, new_engine_version, new_interpretation_version)

    changed_ids = {
        req_id for req_id in old_reqs.keys() | new_reqs.keys()
        if old_reqs.get(req_id) != new_reqs.get(req_id)
    }
    impacted = set()
    for req_id in changed_ids:
        if req_id in old_reqs:
            impacted.add(old_reqs[req_id].scope)
        if req_id in new_reqs:
            impacted.add(new_reqs[req_id].scope)

    current_scopes = all_scopes(new_reqs)
    output = {g: evidence for g, evidence in old_evidence.items()
              if g in current_scopes and g not in impacted}
    for scope in sorted(impacted & current_scopes):
        output[scope] = summarize_scope(
            scope, [r for r in new_reqs.values() if r.scope == scope],
            new_engine_version, new_interpretation_version)
    return output, len(impacted & current_scopes)


def make_requirements(group_count=2000, reqs_per_group=4):
    reqs = {}
    for g in range(group_count):
        scope = f'password_policy_{g:04d}'
        for j in range(reqs_per_group):
            operator = '>=' if j % 2 == 0 else '<='
            value = 8 + j if operator == '>=' else 20 + j
            req_id = f'R-{g:04d}-{j}'
            reqs[req_id] = Requirement(req_id, scope, operator, value)
    return reqs


def run():
    original = make_requirements()
    base_evidence, base_checks = verify_full(original)
    checks = []
    target = 'R-0037-1'
    # Raise one upper limit? No: lower it to force a conflict.
    modified = dict(original)
    modified[target] = replace(modified[target], value=2, text_revision=1)
    checks.append(('value edit introduces conflict', modified, {}))

    # Add, delete and move a requirement into a different existing scope.
    added = dict(original)
    added['R-new'] = Requirement('R-new', original[target].scope, '<=', 1)
    checks.append(('requirement added', added, {}))
    deleted = dict(original)
    deleted.pop(target)
    checks.append(('requirement deleted', deleted, {}))
    moved = dict(original)
    moved[target] = replace(moved[target], scope='password_policy_0038')
    checks.append(('requirement moves scope', moved, {}))
    reworded = dict(original)
    reworded[target] = replace(reworded[target], text_revision=12)
    checks.append(('meaning-preserving rewording (conservative)', reworded, {}))
    checks.append(('parser/interpretation update', original,
                   {'old_interpretation_version': 'v1',
                    'new_interpretation_version': 'v2'}))
    checks.append(('solver version update', original,
                   {'old_engine_version': 'v1', 'new_engine_version': 'v2'}))
    checks.append(('unknown cross-scope dependencies', modified,
                   {'cross_scope_dependencies_known': False}))

    print('SRS GUARDIAN P0 SYNTHETIC FEASIBILITY BENCHMARK')
    print(f'requirements={len(original)}; independent scopes={base_checks}')
    for name, candidate, kwargs in checks:
        full, full_n = verify_full(candidate, kwargs.get('new_engine_version', 'v1'),
                                 kwargs.get('new_interpretation_version', 'v1'))
        incr, inc_n = verify_incremental(original, candidate, base_evidence, **kwargs)
        assert incr == full, f'MISMATCH: {name}'
        print(f'PASS {name}: full_checks={full_n}, incremental_checks={inc_n}, '
              f'same_evidence=True')

    rng = random.Random(51)
    for i in range(120):
        req_id = rng.choice(list(original))
        change = dict(original)
        change[req_id] = replace(change[req_id], value=rng.randint(-15, 30),
                                 text_revision=i + 100)
        full, _ = verify_full(change)
        inc, _ = verify_incremental(original, change, base_evidence)
        assert inc == full, f'Randomized case {i} mismatch'
    print('PASS 120 seeded random single-requirement edits (evidence identical)')

    # Timing is informative only for this synthetic, rule-only workload.
    times_full, times_inc = [], []
    for _ in range(10):
        t = perf_counter()
        verify_full(modified)
        times_full.append(perf_counter()-t)
        t = perf_counter()
        verify_incremental(original, modified, base_evidence)
        times_inc.append(perf_counter()-t)
    print(f'median_full_ms={median(times_full)*1000:.2f}')
    print(f'median_incremental_ms={median(times_inc)*1000:.2f}')
    print('LIMITATION: no real SRS parsing, NLI, SMT, patent novelty, or cross-document validation.')

if __name__ == '__main__':
    run()
