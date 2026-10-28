# Focused retrieval experiment — ACTUAL measured outcome (28 October 2026)

**Result: NO algorithmic improvement. Reject the proposed character TF-IDF and RRF candidates for deployment.**

## Reproduction

GitHub Actions: https://github.com/GoutamNandhen/SRS_Guardian/actions/runs/40720041213

- Run completed successfully, **14 first-party tests passed** (focused unit tests + existing M42 regression tests).
- Both pinned pip before/after source trees passed Git-blob verification; upstream Python source was parsed as inert AST text and **not executed**.
- Full first-party `src/pip/_internal/**/*.py` implementation corpus, with three previously inspected scenario texts at two pinned revisions, not oracle preselected files.
- Ranking methods and parameters were committed before the CI experiment. Historical known fix locus was evaluated only after ranking.

| Method | Known historical fix locus top-1 | Top-5 | Top-10 |
|---|---:|---:|---:|
| Existing original M2 BM25 | 0/6 | 1/6 | 1/6 |
| Existing M42 generic inflection-normalized BM25 | 0/6 | **2/6** | 2/6 |
| New 3–5 character n-gram TF-IDF on code/text/path | 0/6 | 0/6 | 0/6 |
| New normalized-BM25/char-TFIDF reciprocal-rank fusion | 0/6 | 1/6 | 2/6 |

**Not an accuracy metric:** the known historical fix locus is not independently adjudicated requirement-to-code gold. Six rows represent only three correlated scenarios and two versions from one development project. All six behavioral decisions abstain. Independent conformance accuracy, violation precision, violation recall and coverage remain **undefined**.

## Scientific decision

1. **Reject** character n-grams and naive RRF as replacements for M42. No improvement in this bounded real-source diagnostic.
2. **Do not tune against the same six previously inspected cases.** Further method changes here would become post-hoc overfitting.
3. **Shift next resources to independently labeled complete-repository trace pairs and approved runtime observations** from at least three distinct projects. The existing M20/M35/M39/M47/M48 human review process has not received actual independent submissions.
4. Freeze a meaningful baseline and pre-register unseen-project evaluation. Until real gold labels exist, do not report a valid 95% metric.
5. The preliminary research manuscript is available now. It must present this as a negative exploratory development result (optionally in limitations or supplementary study), not as an improved state-of-the-art algorithm.

## Important honesty boundary

- No additional milestone gates or UI can create missing human adjudications.
- No paper claiming verified >=95% real-world conformance can be submitted truthfully from current evidence.
- `main` is unchanged; experiment remains a draft PR for audit, **not a recommended merge**.
