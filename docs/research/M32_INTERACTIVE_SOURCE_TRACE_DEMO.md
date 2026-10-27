# M32 — Interactive source-grounded trace replay (internal demonstration)

## One bounded implementation step

M32 turns the existing M31 two-project source-linked evidence casebook into a clickable, **step-by-step conditional verification demonstration**. A reviewer or faculty member can choose either historical Eclipse EDC pagination scenario, inspect the before/after model's per-contract-definition query offsets, limits, emitted offers, and follow 12 pinned Java source-expression links. The independent pip project remains explicitly **ABSTAIN_NO_BEHAVIORAL_MODEL** for its three historical scenarios. No unsupported pip behavioral prediction is introduced.

This is an **interactive replay of M30's first-party Python abstraction**, not Java execution, proof of complete EDC semantics, independent behavioral ground truth, or research accuracy. The two EDC expectations originate from the upstream issue reporter and remain unadjudicated.

## Reproduce

From repository root, using only first-party Python plus pytest:

~~~bash
python -m pip install 'pytest==8.4.2'
python -m pytest -q backend/tests/test_m20_annotation_queue.py backend/tests/test_m28_historical_pagination_regression.py backend/tests/test_m29_pip_historical_regression.py backend/tests/test_m30_static_pagination_witness.py backend/tests/test_m31_two_project_casebook.py backend/tests/test_m32_interactive_source_trace_demo.py
python -m backend.evaluation.m32_interactive_source_trace_demo --out-dir /tmp/m32
~~~

Open `/tmp/m32/internal/replay.html` locally in a browser. It contains two selectable scenarios, definition-by-definition model traces, explicit assumptions, verified source anchors and pip abstentions. `/tmp/m32/internal/replay.json` is the machine-readable trace, while `/tmp/m32/internal/casebook.json` preserves M31's source-linked inventory.

## Source and license provenance

M32 reuses M31's pinned upstream snapshots, not mutable HEAD:

| Project | License checked by prior pipeline | Upstream evidence | Before / after commits | M32 output |
| --- | --- | --- | --- | --- |
| Eclipse EDC Connector | Apache-2.0 | issue #2493 / fix #2494 | `3d0bd14d62f2fc29762027e94c5f778c90991228` / `bab97cccf4d61a3a380a1d70925b34f4cec1b401` | 2 conditional before/after pagination traces, 12 pinned Java expression anchors |
| pypa/pip | MIT | issue #12372 / fix #12392 | `9685f64fe8c78e1e39cd9b32e5615f42e0a01f1c` / `417ca92b439dba33d707b5da2493358863256bc3` | 3 explicit behavioral-model abstentions |

M31's static fetch verifies six revision/path Git objects per project, including license, implementation and test snapshots. This does not establish complete dependency licensing, a runnable upstream deployment, or that the issue reports are correct.

## Conditional trace examples (NOT runtime)

Under M30's explicit two-definition, 50-assets-each, one-offer-per-asset assumptions:

| Offset | Limit | Before Python model | After Python model | Upstream expected, unadjudicated |
| ---: | ---: | ---: | ---: | ---: |
| 0 | 52 | 100 | 52 | 52 |
| 49 | 2 | 3 | 2 | 2 |

The HTML reveals each definition's query offset, query limit and emitted count, with links to pinned Java expressions. This is a **source-bound explanatory abstraction**, not execution of the third-party Java project. There is no conformance or violation verdict.

## Review and evaluation blockers

The M20 reviewer packets remain separately under `/tmp/m32/{edc,pip}/reviewers/`; never distribute `internal/` to blinded annotators. Two independent reviewers must assess **10 requirement-to-code/test pairs and 10 behavior/revision cases each**, cite source lines and independently establish version-compatible runtime or archived execution evidence. A third adjudicator must resolve disagreements. Only then should a frozen verification method be evaluated on separate unseen projects with explicit eligible denominators, abstentions, coverage and per-project confusion matrices.

**Independent adjudications: 0. Conformance accuracy: NULL. Violation precision: NULL. Violation recall: NULL. Conformance coverage: NULL.** The >=95%, >=95%, >=90% targets remain unproven. No external project code executed. Keep draft PR unmerged and main unchanged.

M32 is a bounded end-to-end demonstration improvement, **not** a new benchmark gate or claim of independent validation.
