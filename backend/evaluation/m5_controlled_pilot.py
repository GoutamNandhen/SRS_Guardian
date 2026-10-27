"""M5 synthetic transfer-rule fault pilot: actual ASGI HTTP behavior, not a research dataset.

Uses trusted in-memory FastAPI fixtures only. No Docker or uploaded-code execution.
This pilot exposes missed narrow faults under fixed boundary test budgets.
"""
from __future__ import annotations

import asyncio
import hashlib
import json
from collections import defaultdict
from fastapi import FastAPI
from httpx import ASGITransport, AsyncClient

from backend.app.services.conformance_verification import parse_transfer_rule

THRESHOLDS = (2500, 5000, 10000, 20000, 45000)
VARIANTS = ("correct", "wide_accept", "accept_at_plus_2", "always_reject")


def approved_fixture(threshold: int, variant: str) -> FastAPI:
    if variant not in VARIANTS:
        raise ValueError("Only predefined trusted fixtures are supported")
    app = FastAPI()

    @app.post("/payments/transfer")
    def submit_transfer(payload: dict):
        value = payload.get("amount")
        if type(value) is not int or value < 0:
            return {"accepted": False}
        if variant == "correct":
            accepted = value <= threshold
        elif variant == "wide_accept":
            accepted = value <= threshold + 1000
        elif variant == "accept_at_plus_2":
            accepted = value <= threshold or value == threshold + 2
        else:
            accepted = False
        return {"accepted": accepted}
    return app


def _case_amounts(threshold: int, strategy: str) -> list[int]:
    wide = threshold + max(2, (threshold + 9) // 10)
    if strategy == "boundary_one":
        return [threshold + 1]
    if strategy == "m3_two_probes":
        return [threshold + 1, wide]
    if strategy == "m5_three_probes":
        return [threshold + 1, threshold + 2, wide]
    raise ValueError("Unknown approved test strategy")


async def run_one(app: FastAPI, threshold: int, strategy: str) -> dict:
    observations = []
    async with AsyncClient(transport=ASGITransport(app=app),
                           base_url="http://fixed-test-fixture.invalid", timeout=5.0) as client:
        for amount in _case_amounts(threshold, strategy):
            response = await client.post("/payments/transfer", json={"amount": amount})
            payload = response.json()
            value = payload.get("accepted")
            verdict = "inconclusive" if response.status_code != 200 or type(value) is not bool else "violates" if value else "passed_check"
            observations.append({"amount": amount, "http_status": response.status_code,
                                 "observed_accepted": value, "verdict": verdict})
    any_bad = any(obs["verdict"] == "violates" for obs in observations)
    any_unknown = any(obs["verdict"] == "inconclusive" for obs in observations)
    decision = "violates" if any_bad else "inconclusive" if any_unknown else "conforms_on_probes_only"
    return {"decision": decision, "observations": observations}


async def run_pilot() -> dict:
    records = []
    methods = ("boundary_one", "m3_two_probes", "m5_three_probes")
    for threshold in THRESHOLDS:
        rule = parse_transfer_rule(f"REQ-SYN-{threshold}",
                                   f"The service shall reject transfers exceeding ₹{threshold:,}.")
        assert rule.threshold == threshold
        for variant in VARIANTS:
            app = approved_fixture(threshold, variant)
            expected = "violates" if variant in {"wide_accept", "accept_at_plus_2"} else "conforms"
            predictions = {}
            for method in methods:
                predictions[method] = await run_one(app, threshold, method)
            records.append({"case_id": f"synthetic-{threshold}-{variant}",
                            "fixture_family": "same_transfer_template_not_cross_project",
                            "threshold": threshold, "fault_variant": variant,
                            "known_ground_truth": expected,
                            "systems": predictions})
    metrics = {}
    for method in methods:
        tp = tn = fp = fn = abstained = 0
        missed = []
        for r in records:
            raw = r["systems"][method]["decision"]
            pred = "conforms" if raw == "conforms_on_probes_only" else raw
            truth = r["known_ground_truth"]
            if pred == "inconclusive":
                abstained += 1
            elif pred == truth == "violates":
                tp += 1
            elif pred == truth == "conforms":
                tn += 1
            elif pred == "violates":
                fp += 1
            else:
                fn += 1
                missed.append(r["case_id"])
        n = len(records)
        metrics[method] = {
            "tp": tp, "tn": tn, "fp": fp, "fn": fn, "abstained": abstained,
            "accuracy_on_constructed_fixtures_full_denominator": (tp + tn) / n,
            "violation_recall_on_constructed_fixtures": tp/(tp+fn) if tp+fn else None,
            "missed_variants": missed,
            "requests_per_case": len(_case_amounts(THRESHOLDS[0], method)),
        }
    return {
        "pilot_type": "CONTROLLED_SYNTHETIC_NON_PUBLICATION_EVALUATION",
        "fixture_count": len(records),
        "distinct_project_count": 0,
        "independent_human_label_count": 0,
        "benchmark_95_eligible": False,
        "method_comparison": metrics,
        "cases": records,
        "limitations": [
            "All 20 fixtures share one transfer-rule template and five numeric thresholds; they are not 20 independently sampled projects.",
            "The code, test oracles and truth labels are author-constructed, not blind human-adjudicated ground truth.",
            "A pass proves no violation in the tested inputs only; untested inputs can still violate a requirement.",
            "This pilot measures no requirement-to-code retrieval accuracy, model generalization or real-world 95% accuracy.",
            "Three probes may still miss narrow defects and do not constitute formal verification.",
        ],
    }


def main() -> int:
    import argparse
    from pathlib import Path
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--out", type=Path)
    args = parser.parse_args()
    report = asyncio.run(run_pilot())
    rendered = json.dumps(report, ensure_ascii=False, indent=2) + "\n"
    if args.out:
        args.out.parent.mkdir(parents=True, exist_ok=True)
        args.out.write_text(rendered, encoding="utf-8")
    print(json.dumps({k: v for k, v in report.items() if k != "cases"}, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
