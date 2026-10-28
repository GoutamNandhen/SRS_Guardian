"""M35: offline, blinded reviewer workspaces for M20 links and behavior cases.

Generates independent, browser-editable annotation handoffs from M31's pinned,
hash-verified two-project reviewer packets. No upstream code is executed.
No labels are inferred, and no adjudication or accuracy is claimed.
"""
from __future__ import annotations

import argparse
from html import escape
import json
from pathlib import Path

from backend.evaluation import m31_two_project_casebook as m31

PROJECTS = ("edc", "pip")
REVIEWERS = ("A", "B")
EXPECTED = {"edc": (4, 4), "pip": (6, 6)}
ANNOTATION_KEYS = {
    "link": ("link_label", "evidence_notes", "annotation_status"),
    "behavior": (
        "observed_offers", "observed_behavior", "conformance_label",
        "violation_label", "approved_runtime_evidence", "reviewer_notes",
        "independent_reviewer_notes", "status",
    ),
}

PAGE = r"""<!doctype html>
<html lang="en"><head><meta charset="utf-8">
<meta name="viewport" content="width=device-width,initial-scale=1">
<title>SRS Guardian — independent review</title>
<style>
body{font:16px system-ui,sans-serif;color:#17283b;background:#f4f7fb;max-width:960px;margin:30px auto;padding:0 16px}
header,article,footer{background:white;border:1px solid #d7e0ea;border-radius:12px;padding:22px;margin:14px 0}
h1,h2{margin:0 0 12px}p{line-height:1.55}article{border-left:4px solid #366bb5}
label{display:block;font-weight:600;margin:12px 0 4px}select,textarea,input{box-sizing:border-box;width:100%;padding:10px;font:inherit;border:1px solid #aab9c9;border-radius:6px}
textarea{min-height:80px}button{background:#135b9d;color:white;border:0;padding:11px 15px;border-radius:7px;cursor:pointer;margin:6px 6px 6px 0}
button:focus-visible{outline:3px solid #f6b84e}small{color:#47596a}a{word-break:break-all}
.warning{background:#fff5df;border-left:5px solid #b9771a;padding:12px}.meta{color:#47596a}
</style></head><body>
<header><h1>Independent annotation workspace</h1>
<p id="identity"></p><p class="warning"><strong>Not ground truth.</strong>
You are reviewing unlabeled source links and behavior cases. Do not infer outcomes
from upstream fixes, reporter claims, static models or expected test results.
Use independently approved, revision-compatible execution records for behavioral verdicts.
Keep your work separate from the other reviewer; a third person adjudicates later.</p>
<p id="progress" aria-live="polite"></p>
<button id="export-links">Export link JSONL</button>
<button id="export-behaviors">Export behavior JSONL</button>
<label for="restore">Restore your own previously exported JSONL (optional)</label>
<input type="file" id="restore" accept=".jsonl,.txt,application/json">
<small>All editing occurs in this browser tab. No uploads, network calls or automatic saving.
Export both files before closing. Pending cases remain null.</small>
</header>
<section id="links"><h2>Requirement-to-code links</h2></section>
<section id="behaviors"><h2>Behavior at pinned revision</h2></section>
<footer><p><strong>Review handoff:</strong> export both JSONL files for your project.
Two independent reviewers assess each case; a separate adjudicator resolves disagreements.
This workspace does not calculate research accuracy, precision, recall or coverage.</p></footer>
<script type="application/json" id="seed">__PAYLOAD__</script>
<script>
"use strict";
const data=JSON.parse(document.getElementById("seed").textContent);
const initial=structuredClone(data);
document.getElementById("identity").textContent=
  "Project: "+data.project+" · Reviewer: "+data.reviewer+
  " · "+data.links.length+" links · "+data.behaviors.length+" behavior/revision cases";
function el(tag,text){const n=document.createElement(tag);if(text!==undefined)n.textContent=String(text);return n;}
function addText(parent,tag,text){const n=el(tag,text);parent.append(n);return n;}
function field(parent,title,value,handler,multiline=false){
  const label=addText(parent,"label",title);
  const input=document.createElement(multiline?"textarea":"input");
  if(!multiline)input.type="text";
  input.value=value??"";input.addEventListener("input",()=>{handler(input.value);progress();});
  label.append(input);return input;
}
function choice(parent,title,options,current,handler){
  const label=addText(parent,"label",title),select=el("select");
  for(const [value,title] of options){const opt=el("option",title);opt.value=value;select.append(opt);}
  select.value=current;select.addEventListener("change",()=>{handler(select.value);progress();});
  label.append(select);return select;
}
function url(parent,title,value){
  if(!value)return;
  const row=addText(parent,"p",title+": ");
  try{const parsed=new URL(value);if(parsed.protocol!=="https:"||parsed.hostname!=="github.com")return;
    const a=el("a",value);a.href=parsed.href;a.target="_blank";a.rel="noopener noreferrer";row.append(a);
  }catch(_e){}
}
function progress(){
  const linked=data.links.filter(x=>x.annotation_status==="reviewed").length;
  const observed=data.behaviors.filter(x=>x.status==="reviewed").length;
  document.getElementById("progress").textContent=
    "Completed with evidence: "+linked+"/"+data.links.length+" links; "+
    observed+"/"+data.behaviors.length+" behavior cases. Unresolved labels stay null.";
}
function render(){
  for(const type of ["links","behaviors"]){
    const section=document.getElementById(type);
    section.querySelectorAll("article").forEach(n=>n.remove());
    for(const row of data[type]){
      const card=el("article");section.append(card);
      addText(card,"h3",row.case_id+(row.revision?" · "+row.revision:""));
      if(type==="links"){
        addText(card,"p","Requirement: "+row.requirement_text);
        addText(card,"p","Source: "+row.source_path+" · "+row.qualified_name);
        if(row.description)addText(card,"small",row.description);
        const label=choice(card,"Link judgment",[
          ["","Unreviewed / unknown"],["linked","Linked"],["not_linked","Not linked"],["uncertain","Uncertain"]
        ],row.link_label??"",v=>{row.link_label=v||null;refreshLink(row);});
        field(card,"Exact source-line citation and reasoning",row.evidence_notes,v=>{
          row.evidence_notes=v.trim()||null;refreshLink(row);
        },true);
        function refreshLink(r){
          r.annotation_status=r.link_label&&r.link_label!=="uncertain"&&r.evidence_notes?"reviewed":"pending";
        }
      }else{
        addText(card,"p","Expected behavior candidate: "+
          (row.expected_behavior??("Expected offer count: "+row.expected_offers)));
        if(row.offset!==undefined)addText(card,"small","Offset "+row.offset+"; limit "+row.limit);
        url(card,"Pinned source",row.source_url);url(card,"Pinned test",row.test_url);
        choice(card,"Evidence-supported verdict",[
          ["","Pending / unknown"],["conformant","Conformant"],["violating","Violating"]
        ],row.conformance_label===true?"conformant":row.violation_label===true?"violating":"",v=>{
          row.conformance_label=v==="conformant"?true:v==="violating"?false:null;
          row.violation_label=v==="violating"?true:v==="conformant"?false:null;
          refreshBehavior(row);
        });
        const observedKey=Object.hasOwn(row,"observed_offers")?"observed_offers":"observed_behavior";
        field(card,"Observed result from independent execution/log",row[observedKey],v=>{
          row[observedKey]=v.trim()||null;refreshBehavior(row);
        });
        field(card,"Approved runtime evidence URL, artifact ID or log citation",
          row.approved_runtime_evidence,v=>{
            row.approved_runtime_evidence=v.trim()||null;refreshBehavior(row);
          });
        const notesKey=Object.hasOwn(row,"independent_reviewer_notes")?
          "independent_reviewer_notes":"reviewer_notes";
        field(card,"Revision, fixture, environment and rationale",row[notesKey],v=>{
          row[notesKey]=v.trim()||null;refreshBehavior(row);
        },true);
        function refreshBehavior(r){
          r.status=r.conformance_label!==null&&r.violation_label!==null&&
            r[observedKey]!==null&&r.approved_runtime_evidence&&r[notesKey]?
            "reviewed":"pending";
        }
      }
    }
  }
  progress();
}
function download(type){
  const lines=data[type].map(row=>JSON.stringify(row)).join("\n")+"\n";
  const blob=new Blob([lines],{type:"application/x-ndjson;charset=utf-8"});
  const href=URL.createObjectURL(blob),a=el("a");
  a.href=href;a.download=data.project+"_"+type+"_reviewer_"+data.reviewer+".jsonl";
  document.body.append(a);a.click();a.remove();setTimeout(()=>URL.revokeObjectURL(href),1500);
}
document.getElementById("export-links").onclick=()=>download("links");
document.getElementById("export-behaviors").onclick=()=>download("behaviors");
document.getElementById("restore").addEventListener("change",async e=>{
  const file=e.target.files[0];if(!file)return;
  try{
    const rows=(await file.text()).split(/\r?\n/).filter(Boolean).map(x=>JSON.parse(x));
    if(!rows.length)throw Error("Empty file");
    const type=Object.hasOwn(rows[0],"requirement_id")?"links":"behaviors";
    const original=initial[type],byId=new Map(original.map(r=>[
      r.case_id+(r.revision?"|"+r.revision:""),r]));
    if(rows.length!==original.length)throw Error("Wrong number of cases");
    const seen=new Set();
    for(const r of rows){
      const key=r.case_id+(r.revision?"|"+r.revision:"");
      const source=byId.get(key);
      if(!source||seen.has(key)||r.reviewer!==source.reviewer)throw Error("Wrong reviewer or case");
      seen.add(key);
      const allowed=type==="links"?
        ["link_label","evidence_notes","annotation_status"]:
        ["observed_offers","observed_behavior","conformance_label","violation_label",
         "approved_runtime_evidence","reviewer_notes","independent_reviewer_notes","status"];
      for(const k of Object.keys(source)){
        if(!allowed.includes(k)&&JSON.stringify(r[k])!==JSON.stringify(source[k]))
          throw Error("Immutable case fields changed: "+k);
      }
    }
    data[type]=rows;render();alert("Restored "+type+" for reviewer "+data.reviewer);
  }catch(error){alert("Import rejected: "+error.message);}
  e.target.value="";
});
render();
</script></body></html>"""


def read_packet(path: Path, expected_count: int, reviewer: str, *, behavior: bool) -> list[dict]:
    rows = [json.loads(line) for line in path.read_text(encoding="utf-8").splitlines() if line.strip()]
    if len(rows) != expected_count:
        raise ValueError(f"Wrong reviewer case count in {path}")
    ids = set()
    for row in rows:
        if row.get("reviewer") != (reviewer if behavior else f"reviewer_{reviewer}"):
            raise ValueError(f"Reviewer contamination in {path}")
        key = (row.get("case_id"), row.get("revision"))
        if key in ids:
            raise ValueError(f"Duplicate case {key}")
        ids.add(key)
        if behavior:
            if row.get("conformance_label") is not None or row.get("violation_label") is not None:
                raise ValueError("Unexpected pre-labeled behavior")
            if row.get("status") != "pending":
                raise ValueError("Unexpected behavioral review status")
        else:
            if row.get("link_label") is not None or row.get("annotation_status") != "pending":
                raise ValueError("Unexpected pre-labeled link")
        if any(k in row for k in ("static_model_before", "static_model_after", "sampling_provenance", "gold_link")):
            raise ValueError("Unblinded material in reviewer packet")
    return rows


def build_workspaces(root: Path) -> dict:
    generated = []
    for project in PROJECTS:
        packet = root / project / "reviewers"
        for reviewer in REVIEWERS:
            n_links, n_behaviors = EXPECTED[project]
            links = read_packet(packet / f"reviewer_{reviewer}.jsonl", n_links, reviewer, behavior=False)
            behaviors = read_packet(packet / f"behavior_reviewer_{reviewer}.jsonl", n_behaviors, reviewer, behavior=True)
            payload = json.dumps({"project": project, "reviewer": reviewer,
                                  "links": links, "behaviors": behaviors}, ensure_ascii=False)
            payload = payload.replace("<", "\\u003c").replace(">", "\\u003e").replace("&", "\\u0026")
            html = PAGE.replace("__PAYLOAD__", payload)
            destination = packet / f"workspace_reviewer_{reviewer}.html"
            destination.write_text(html, encoding="utf-8")
            generated.append({"project": project, "reviewer": reviewer,
                              "links_pending": len(links), "behavior_cases_pending": len(behaviors),
                              "workspace": str(destination.relative_to(root))})
    manifest = {
        "schema": "m35-independent-review-workspace-1",
        "projects": 2, "workspaces": generated, "independent_adjudications": 0,
        "external_project_code_executed": False, "held_out_evaluation": False,
        "metrics": {name: None for name in m31.METRICS},
        "next_blocker": "Two independent human reviewers must complete source-linked annotations and "
                        "provide approved revision-compatible runtime observations; third-party adjudication "
                        "and frozen-verifier held-out project evaluation remain pending.",
    }
    (root / "review_handoff_manifest.json").write_text(
        json.dumps(manifest, indent=2) + "\n", encoding="utf-8")
    return manifest


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--out-dir", required=True, type=Path)
    args = parser.parse_args(argv)
    m31.main(["--out-dir", str(args.out_dir)])
    manifest = build_workspaces(args.out_dir)
    print(json.dumps({"workspaces": len(manifest["workspaces"]),
                      "adjudications": 0, "metrics": manifest["metrics"]}, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
