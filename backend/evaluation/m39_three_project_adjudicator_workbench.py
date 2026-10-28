"""M39: three-project, offline human adjudication workbench.

Consumes *submitted* independent M35/M38 reviewer JSONL, never upstream code.
Does not promote reviewer agreement to gold or compute research accuracy.
"""
from __future__ import annotations

import argparse
import json
from pathlib import Path

from backend.evaluation import m36_adjudication_handoff as m36

PROJECTS = {"edc": (4, 4), "pip": (6, 6), "werkzeug": (6, 4)}
PAGE = r"""<!doctype html><html lang="en"><head><meta charset="utf-8">
<meta name="viewport" content="width=device-width,initial-scale=1">
<title>SRS Guardian — independent adjudicator workbench</title>
<style>
body{font:16px system-ui,sans-serif;background:#f4f7fa;color:#192b3b;max-width:1050px;margin:24px auto;padding:0 16px}
header,article{background:white;border:1px solid #d5e0e9;border-radius:12px;padding:20px;margin:16px 0}
article{border-left:5px solid #507cad}label{display:block;margin:12px 0 5px;font-weight:600}
input,select,textarea{width:100%;box-sizing:border-box;font:inherit;padding:9px;border:1px solid #9baebd;border-radius:6px}
textarea{min-height:75px}button{padding:12px 18px;background:#135d9b;color:white;border:0;border-radius:6px;cursor:pointer}
.warning{padding:12px;background:#fff1d8;border-left:5px solid #ba7620}
pre{white-space:pre-wrap;overflow-wrap:anywhere;background:#f2f5f8;padding:10px}
small{color:#425466}
</style></head><body><header><h1>Independent adjudication — three projects</h1>
<p class="warning"><strong>Not ground truth yet.</strong> Reviewer agreement never creates a gold label.
This page is for a separate human adjudicator. Review pinned requirements, source lines,
independent A/B submissions, and approved revision-compatible runtime records.
Do not use this workbench for blinded reviewers or tune the verifier on these cases.
Incomplete A/B cases cannot be finalized here.</p>
<p id="summary"></p><button id="export">Export adjudicator JSONL</button>
<p><small>Offline only; nothing is saved or uploaded. Export before closing.
An exported decision is an attributable human claim, not proof of independence.
No research performance metrics are calculated.</small></p></header>
<main id="cases"></main><script type="application/json" id="seed">__PAYLOAD__</script>
<script>
"use strict";
const tasks=JSON.parse(document.getElementById("seed").textContent);
function el(tag,txt){const x=document.createElement(tag);if(txt!==undefined)x.textContent=String(txt);return x;}
function field(card,label,value,change,multi){
  const wrapper=el("label",label), input=el(multi?"textarea":"input");
  if(!multi)input.type="text";input.value=value??"";
  input.addEventListener("input",()=>{change(input.value.trim()||null);update();});
  wrapper.append(input);card.append(wrapper);
}
function choice(card,t,options,current,change){
  const wrapper=el("label",t),input=el("select");
  for(const [value,name] of options){const option=el("option",name);option.value=value;input.append(option);}
  input.value=current;input.addEventListener("change",()=>{change(input.value);update();});
  wrapper.append(input);card.append(wrapper);
}
function valid(t){
  const label=t.adjudicated_label;
  const correct=t.kind==="link"?["linked","not_linked"].includes(label):typeof label==="boolean";
  return t.comparison!=="pending_or_incomplete"&&correct&&
    !!t.adjudicator_identity&&!!t.adjudication_evidence&&!!t.adjudication_rationale&&
    (t.kind!=="behavior"||!!t.adjudication_runtime_evidence);
}
function update(){
  for(const t of tasks)t.adjudication_status=valid(t)?"adjudicated":"pending";
  const done=tasks.filter(t=>t.adjudication_status==="adjudicated").length;
  document.getElementById("summary").textContent=done+"/"+tasks.length+
    " attributable decisions with evidence entered; NOT independently validated or scored.";
}
for(const t of tasks){
  const card=el("article");document.getElementById("cases").append(card);
  card.append(el("h2",t.project+" · "+t.kind+" · "+t.case_id+
    (t.revision?" · "+t.revision:"")));
  card.append(el("p","Reviewer comparison: "+t.comparison));
  card.append(el("pre","Pinned case evidence: "+JSON.stringify(t.source,null,2)));
  card.append(el("pre","Reviewer A: "+JSON.stringify(t.reviewer_A,null,2)));
  card.append(el("pre","Reviewer B: "+JSON.stringify(t.reviewer_B,null,2)));
  if(t.comparison==="pending_or_incomplete"){
    card.append(el("p","Await two complete, evidence-backed independent submissions; no final verdict permitted."));
    continue;
  }
  const options=t.kind==="link"?
    [["","Unknown / unresolved"],["linked","Linked"],["not_linked","Not linked"]]:
    [["","Unknown / unresolved"],["true","Conformant"],["false","Violating"]];
  const current=t.adjudicated_label===null?"":String(t.adjudicated_label);
  choice(card,"Adjudicator decision (never inferred from reviewer agreement)",options,current,v=>{
    t.adjudicated_label=v===""?null:t.kind==="link"?v:v==="true";
  });
  field(card,"Adjudicator identity (must be separate from reviewers)",t.adjudicator_identity,
    v=>{t.adjudicator_identity=v;});
  field(card,"Exact requirement/source-line evidence or artifact reference",t.adjudication_evidence,
    v=>{t.adjudication_evidence=v;},true);
  if(t.kind==="behavior")field(card,"Approved runtime evidence, pinned revision, fixture and environment",
    t.adjudication_runtime_evidence,v=>{t.adjudication_runtime_evidence=v;},true);
  field(card,"Independent rationale, including disagreement resolution",t.adjudication_rationale,
    v=>{t.adjudication_rationale=v;},true);
}
update();
document.getElementById("export").addEventListener("click",()=>{
  update();const content=tasks.map(t=>JSON.stringify(t)).join("\n")+"\n";
  const url=URL.createObjectURL(new Blob([content],{type:"application/x-ndjson"}));
  const a=el("a");a.href=url;a.download="m39_adjudicator_decisions_NOT_GOLD.jsonl";
  document.body.append(a);a.click();a.remove();setTimeout(()=>URL.revokeObjectURL(url),1500);
});
</script></body></html>"""


def _werkzeug_tasks(root: Path) -> list[dict]:
    folder = root / "werkzeug" / "reviewers"
    tasks = []
    for kind, expected in (("link", 6), ("behavior", 4)):
        name = "reviewer_{}.jsonl" if kind == "link" else "behavior_reviewer_{}.jsonl"
        left = m36.load(folder / name.format("A"), expected, "A", kind)
        right = m36.load(folder / name.format("B"), expected, "B", kind)
        if left.keys() != right.keys():
            raise ValueError("Reviewer case universe mismatch: werkzeug/" + kind)
        for key in sorted(left):
            a, b = left[key], right[key]
            if m36.immutable(a) != m36.immutable(b):
                raise ValueError("Immutable evidence differs: werkzeug/" + kind)
            complete = m36.valid_decision(a, kind) and m36.valid_decision(b, kind)
            label = "link_label" if kind == "link" else "conformance_label"
            comparison = ("pending_or_incomplete" if not complete else
                          "reviewer_agreement" if a[label] == b[label] else
                          "reviewer_disagreement")
            tasks.append({
                "project": "werkzeug", "kind": kind, "case_id": key[0],
                "revision": key[1], "source": m36.immutable(a),
                "reviewer_A": {k: v for k, v in a.items() if k in m36.MUTABLE},
                "reviewer_B": {k: v for k, v in b.items() if k in m36.MUTABLE},
                "comparison": comparison, "adjudicated_label": None,
                "adjudicator_identity": None, "adjudication_evidence": None,
                "adjudication_runtime_evidence": None,
                "adjudication_rationale": None, "adjudication_status": "pending",
            })
    return tasks


def generate(review_root: Path, out_dir: Path) -> dict:
    if out_dir.exists() and any(out_dir.iterdir()):
        raise ValueError("Output directory must be empty")
    tasks, _ = m36.reconcile(review_root)
    for task in tasks:
        task["adjudication_runtime_evidence"] = None
        task["adjudication_rationale"] = None
    tasks.extend(_werkzeug_tasks(review_root))
    counts = {name: sum(t["comparison"] == name for t in tasks)
              for name in ("pending_or_incomplete", "reviewer_agreement",
                           "reviewer_disagreement")}
    manifest = {
        "schema": "m39-three-project-human-adjudication-workbench-1",
        "projects": len(PROJECTS), "tasks": len(tasks),
        "cases_per_project": {p: sum(t["project"] == p for t in tasks) for p in PROJECTS},
        "comparison_counts": counts, "independent_adjudications": 0,
        "external_project_code_executed": False,
        "held_out_evaluation": False,
        "metrics": {name: None for name in m36.METRICS},
        "next_blocker": "Obtain real A/B evidence-backed submissions and an independent "
                        "human adjudicator; freeze a verifier before scoring untouched "
                        "held-out projects. Exported workbench data are not automatically gold.",
    }
    out_dir.mkdir(parents=True, exist_ok=True)
    m36.write_outputs(tasks, manifest, out_dir)
    payload = json.dumps(tasks, ensure_ascii=False).replace("<", "\\u003c").replace(">", "\\u003e").replace("&", "\\u0026")
    (out_dir / "adjudicator_workbench.html").write_text(
        PAGE.replace("__PAYLOAD__", payload), encoding="utf-8")
    return manifest


def main(argv: list[str] | None = None) -> int:
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument("--review-root", required=True, type=Path)
    p.add_argument("--out-dir", required=True, type=Path)
    args = p.parse_args(argv)
    print(json.dumps(generate(args.review_root, args.out_dir), indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
