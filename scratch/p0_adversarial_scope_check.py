"""Adversarial gap demonstration for SRS Guardian P0. Not a production verifier."""
from dataclasses import dataclass
from collections import defaultdict

@dataclass(frozen=True)
class Req:
    key: str
    surface_entity: str
    constraint: str
    value: int

# 'credential length' and 'password length' refer to same thing in THIS case.
# In real systems the mapping must be validated rather than assumed.
ALIASES = {'password length':'password length', 'credential length':'password length',
           'username length':'username length'}

def verify(reqs, canonicalize):
    groups=defaultdict(list)
    for r in reqs:
        scope=ALIASES.get(r.surface_entity,r.surface_entity) if canonicalize else r.surface_entity
        groups[scope].append(r)
    out={}
    for scope,rs in groups.items():
        low=max((r.value for r in rs if r.constraint=='>='),default=None)
        high=min((r.value for r in rs if r.constraint=='<='),default=None)
        out[scope]=(low,high,low is not None and high is not None and low>high)
    return out

base=[Req('R1','password length','>=',8),Req('R2','credential length','<=',10)]
changed=[base[0],Req('R2','credential length','<=',6)]
truth=verify(changed,canonicalize=True)
naive=verify(changed,canonicalize=False)
assert truth['password length'][2] is True
assert not any(rec[2] for rec in naive.values())
print('CASE 1: Validated alias dependency; changed upper bound 10 -> 6')
print('  full oracle (aliases resolved) : CONFLICT')
print('  surface-scope verifier          : NO CONFLICT (UNSAFE FALSE NEGATIVE)')

# Requirement text changes entity but a cached scope label is not refreshed.
base=[Req('R1','password length','>=',8),Req('R2','username length','<=',6)]
changed=[base[0],Req('R2','password length','<=',6)]
expected=verify(changed,canonicalize=True)
stale_scope=[base[0],Req('R2','username length','<=',6)]
reused=verify(stale_scope,canonicalize=True)
assert expected['password length'][2] and not any(rec[2] for rec in reused.values())
print('CASE 2: Edit silently changes the entity being constrained')
print('  freshly interpreted full check : CONFLICT')
print('  stale scope reuse               : NO CONFLICT (UNSAFE FALSE NEGATIVE)')

# Conservative fail-closed: unknown relationships force recomputation and human review.
print('CASE 3: Correct response to unknown alias/scope mappings')
print('  mark interpretation UNKNOWN -> do not assert safe incremental reuse')
print('  requires rebuilding link index or full verification, human review if unresolved')
print('NOTE: These are constructed negative tests; no empirical real-world error rates.')
