"use client";

import { useEffect, useState } from "react";
import { FileCode2, Upload, Search, AlertCircle, Loader2, CheckCircle2 } from "lucide-react";
import { api } from "@/services/api";
import type { DocumentListItem } from "@/types";

type CodeIndex = {
  index_id: string;
  label: string;
  files_indexed: number;
  symbols_indexed: number;
  warnings: string[];
  methodology: string;
};
type Candidate = {
  symbol_id: string; path: string; qualified_name: string; kind: string;
  line_start: number; line_end: number; http: {method:string;route:string}[];
  score: number; matched_terms: string[]; evidence_features: string[];
  signature: string; source_excerpt: string; verification_status: string; explanation: string;
};
type TraceResult = {
  document_id: number; index_id: string; index_label: string;
  total_requirements: number; offset: number; limit: number;
  results: {requirement_id:number;req_key:string;text:string;candidates:Candidate[]}[];
  note: string;
};

const API_BASE=process.env.NEXT_PUBLIC_API_URL || "http://127.0.0.1:8000/api";
async function parseError(res:Response):Promise<string>{
  try {const body=await res.json();return typeof body.detail==="string"?body.detail:JSON.stringify(body.detail);}
  catch{return "Request failed ("+res.status+")";}
}
export default function TraceabilityPage(){
  const [docs,setDocs]=useState<DocumentListItem[]>([]);
  const [docId,setDocId]=useState<number|null>(null);
  const [source,setSource]=useState<File|null>(null);
  const [index,setIndex]=useState<CodeIndex|null>(null);
  const [result,setResult]=useState<TraceResult|null>(null);
  const [offset,setOffset]=useState(0);
  const [loading,setLoading]=useState<"none"|"index"|"links">("none");
  const [error,setError]=useState<string|null>(null);
  useEffect(()=>{
    api.getDocuments().then(items=>{
      setDocs(items);
      setDocId(items.find(item=>item.requirement_count>0)?.id??null);
    }).catch((e:Error)=>setError(e.message));
  },[]);

  async function uploadSource(){
    if(!source)return;
    setLoading("index");setError(null);setIndex(null);setResult(null);
    const form=new FormData();
    form.append("file",source);form.append("label",source.name);
    try{
      const r=await fetch(API_BASE+"/code-traceability/index",{method:"POST",body:form});
      if(!r.ok)throw new Error(await parseError(r));
      setIndex(await r.json());setOffset(0);
    }catch(e){setError(e instanceof Error?e.message:"Unable to index source ZIP");}
    finally{setLoading("none");}
  }
  async function searchCode(page=0){
    if(!docId||!index)return;
    setLoading("links");setError(null);setResult(null);
    try{
      const args=new URLSearchParams({index_id:index.index_id,offset:String(page),limit:"20",top_k:"5"});
      const r=await fetch(API_BASE+"/code-traceability/documents/"+docId+"/links?"+args);
      if(!r.ok)throw new Error(await parseError(r));
      setResult(await r.json());setOffset(page);
    }catch(e){setError(e instanceof Error?e.message:"Unable to retrieve code links");}
    finally{setLoading("none");}
  }

  const eligible=docs.filter(d=>d.requirement_count>0);
  return <div className="mx-auto max-w-6xl space-y-6">
    <header>
      <h1 className="text-2xl font-semibold text-on-surface">Requirement-to-Code Traceability</h1>
      <p className="mt-1 text-sm text-on-surface-variant">Find candidate Python/FastAPI implementations for your SRS requirements.</p>
    </header>
    <div className="rounded-lg border border-outline-variant/40 bg-surface-container-low p-4 text-sm text-on-surface-variant">
      <b>Unverified search results:</b> A matched function is not proof of implementation correctness. No uploaded code is executed. Use only authorized repositories and run this prototype on a private/local server.
    </div>
    {error&&<div role="alert" className="flex items-center gap-2 rounded border border-error/40 p-3 text-sm text-error"><AlertCircle className="h-4 w-4"/>{error}</div>}
    <section className="grid gap-4 md:grid-cols-2">
      <div className="space-y-3 rounded-lg border border-outline-variant/40 bg-surface-container-lowest p-5">
        <h2 className="font-semibold">1. Select analyzed SRS</h2>
        <label htmlFor="m2-doc" className="block text-sm text-on-surface-variant">Requirements already extracted</label>
        <select id="m2-doc" className="w-full rounded border border-outline-variant/60 bg-surface p-2 text-sm" value={docId??""} onChange={e=>{setDocId(Number(e.target.value)||null);setOffset(0);setResult(null);}}>
          {!eligible.length&&<option value="">No extracted requirements</option>}
          {eligible.map(d=><option key={d.id} value={d.id}>{d.filename} ({d.requirement_count} requirements)</option>)}
        </select>
        <p className="text-xs text-on-surface-variant">Use Documents to upload and analyze the SRS first.</p>
      </div>
      <div className="space-y-3 rounded-lg border border-outline-variant/40 bg-surface-container-lowest p-5">
        <h2 className="font-semibold">2. Upload authorized Python code</h2>
        <label htmlFor="m2-zip" className="block text-sm text-on-surface-variant">Repository ZIP (8 MB maximum compressed)</label>
        <input id="m2-zip" type="file" accept=".zip,application/zip" className="w-full text-xs text-on-surface-variant" onChange={e=>{setSource(e.target.files?.[0]??null);setIndex(null);setResult(null);}}/>
        <button onClick={uploadSource} disabled={!source||loading!=="none"} className="flex items-center gap-2 rounded bg-primary px-4 py-2 text-sm font-medium text-primary-foreground disabled:opacity-50">
          {loading==="index"?<Loader2 className="h-4 w-4 animate-spin"/>:<Upload className="h-4 w-4"/>} Index code
        </button>
        {index&&<p className="flex items-center gap-2 text-sm text-on-surface-variant"><CheckCircle2 className="h-4 w-4 text-emerald-600"/>{index.files_indexed} files · {index.symbols_indexed} symbols</p>}
        {index&&index.warnings.length>0&&<details className="text-xs"><summary>{index.warnings.length} indexing warnings</summary><ul className="list-disc pl-4">{index.warnings.map((s,i)=><li key={i}>{s}</li>)}</ul></details>}
      </div>
    </section>
    {index&&<section className="rounded-lg border border-outline-variant/40 bg-surface-container-lowest p-5 space-y-2">
      <h2 className="font-semibold">3. Find candidate links</h2>
      <button onClick={()=>searchCode(0)} disabled={!docId||loading!=="none"} className="flex items-center gap-2 rounded bg-primary px-4 py-2 text-sm font-medium text-primary-foreground disabled:opacity-50">
        {loading==="links"?<Loader2 className="h-4 w-4 animate-spin"/>:<Search className="h-4 w-4"/>} Link requirements
      </button>
    </section>}
    {result&&<section className="space-y-4">
      <div className="flex flex-wrap justify-between gap-2">
        <h2 className="text-lg font-semibold">Candidate links</h2>
        <p className="text-xs text-on-surface-variant">Showing {result.results.length?offset+1:0}–{offset+result.results.length} of {result.total_requirements}</p>
      </div>
      <p className="text-xs text-on-surface-variant">Ranking scores are not probability/confidence values. No conformance claims are made.</p>
      {result.results.map(req=><article key={req.requirement_id} className="space-y-3 rounded-lg border border-outline-variant/40 bg-surface-container-lowest p-5">
        <h3 className="text-sm font-semibold">{req.req_key}</h3>
        <p className="text-sm text-on-surface-variant">{req.text}</p>
        {!req.candidates.length?<p className="text-xs text-on-surface-variant">No lexical match found. This does not mean the requirement is unimplemented.</p>:
        req.candidates.map((c,i)=><details key={c.symbol_id} className="rounded border border-outline-variant/40 p-3">
          <summary className="cursor-pointer list-none">
            <div className="flex flex-wrap justify-between gap-2">
              <span className="flex gap-2 items-center text-sm font-medium"><FileCode2 className="h-4 w-4"/>#{i+1} {c.qualified_name}</span>
              <span className="text-xs text-on-surface-variant">Rank score {c.score.toFixed(2)} · Unverified candidate</span>
            </div>
            <p className="mt-1 text-xs text-on-surface-variant">{c.path}:{c.line_start}–{c.line_end}</p>
            {c.http.map((h,j)=><span key={j} className="mr-2 mt-1 inline-block rounded border border-outline-variant/60 px-2 py-0.5 text-xs">{h.method} {h.route}</span>)}
          </summary>
          <div className="mt-3">
            <p className="mb-2 text-xs text-on-surface-variant">Matched terms: {c.matched_terms.join(", ")}</p>
            <pre className="max-h-60 overflow-auto whitespace-pre-wrap break-words rounded bg-surface-container p-3 text-xs">{c.source_excerpt}</pre>
          </div>
        </details>)}
      </article>)}
      <div className="flex justify-end gap-3">
        <button onClick={()=>searchCode(Math.max(0,offset-20))} disabled={loading!=="none"||offset===0} className="rounded border border-outline-variant px-3 py-2 text-sm disabled:opacity-50">Previous</button>
        <button onClick={()=>searchCode(offset+20)} disabled={loading!=="none"||offset+result.results.length>=result.total_requirements} className="rounded border border-outline-variant px-3 py-2 text-sm disabled:opacity-50">Next</button>
      </div>
    </section>}
  </div>;
}
