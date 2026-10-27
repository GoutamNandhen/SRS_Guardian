"""M2 read-only Python/FastAPI AST indexer and BM25-style candidate retrieval.
All returned links are unverified. Uploaded project code is NEVER executed.
"""
from __future__ import annotations
import ast
from collections import Counter
from datetime import datetime, timezone
from hashlib import sha256
from io import BytesIO
import json
import math
import os
from pathlib import Path, PurePosixPath
import re
import stat
import tempfile
import zipfile

MAX_ARCHIVE_BYTES=8*1024*1024
MAX_SOURCE_BYTES=1024*1024
MAX_TOTAL_SOURCE_BYTES=24*1024*1024
MAX_FILES=400
MAX_SYMBOLS=12000
DISALLOWED={".git",".venv","venv","env","__pycache__","node_modules","dist","build",".next","site-packages"}
HTTP_METHODS={"get","post","put","patch","delete","options","head"}
STOPWORDS={"the","shall","should","must","will","may","can","be","is","are","for","in","on","to","of","a","an","and","or","by","with","this","that","it","system","application","service","user","users","when","where","from","any"}

def tokenize(value:str)->list[str]:
    value=re.sub(r"([a-z0-9])([A-Z])",r"\1 \2",value)
    words=re.findall(r"[A-Za-z][A-Za-z0-9]*",value.lower())
    return [w[:-1] if len(w)>4 and w.endswith("s") and not w.endswith("ss") else w for w in words if w not in STOPWORDS and len(w)>2]

def _safe_member_path(name:str)->str|None:
    if "\\" in name or "\x00" in name or name.startswith("/"): return None
    path=PurePosixPath(name)
    parts=path.parts
    if not parts or any(p in {"..","."} for p in parts): return None
    if any(p.lower() in DISALLOWED for p in parts): return None
    if not name.endswith(".py"): return None
    return str(path)

def _is_unsafe_link(info:zipfile.ZipInfo)->bool:
    return stat.S_ISLNK((info.external_attr>>16)&65535)

def _literal_str(node:ast.AST|None)->str|None:
    return node.value if isinstance(node,ast.Constant) and isinstance(node.value,str) else None

def _router_prefixes(module:ast.Module)->dict[str,str]:
    prefixes={}
    for node in module.body:
        if not isinstance(node,(ast.Assign,ast.AnnAssign)):continue
        call=node.value
        if not isinstance(call,ast.Call) or not isinstance(call.func,(ast.Name,ast.Attribute)):continue
        if (call.func.id if isinstance(call.func,ast.Name) else call.func.attr)!="APIRouter":continue
        target=node.targets[0] if isinstance(node,ast.Assign) and node.targets else node.target
        if not isinstance(target,ast.Name):continue
        for key in call.keywords:
            if key.arg=="prefix":
                value=_literal_str(key.value)
                if value is not None:prefixes[target.id]=value
    return prefixes

def _endpoints(node:ast.FunctionDef|ast.AsyncFunctionDef,prefixes:dict[str,str])->list[dict]:
    found=[]
    for deco in node.decorator_list:
        if not isinstance(deco,ast.Call) or not isinstance(deco.func,ast.Attribute):continue
        method=deco.func.attr.lower()
        if method not in HTTP_METHODS and method!="api_route":continue
        receiver=deco.func.value
        if not isinstance(receiver,ast.Name):continue
        route=_literal_str(deco.args[0]) if deco.args else None
        if route is None:
            for k in deco.keywords:
                if k.arg in {"path","path_format"}:route=_literal_str(k.value)
        if route is None:continue
        verbs=[method.upper()]
        if method=="api_route":
            verbs=[]
            for k in deco.keywords:
                if k.arg=="methods" and isinstance(k.value,(ast.List,ast.Tuple)):
                    verbs=[v.value.upper() for v in k.value.elts if isinstance(v,ast.Constant) and isinstance(v.value,str)]
        prefix=prefixes.get(receiver.id,"")
        full_route=f"{prefix.rstrip('/')}/{route.lstrip('/')}" if prefix else route
        for verb in verbs:
            if verb in {v.upper() for v in HTTP_METHODS}:found.append({"method":verb,"route":full_route})
    return found

def _index_python(path:str,source:str)->tuple[list[dict],str|None]:
    try:tree=ast.parse(source,filename=path)
    except (SyntaxError,ValueError) as exc:
        return [],f"Skipped {path}: Python parse error ({type(exc).__name__})"
    lines=source.splitlines()
    prefixes=_router_prefixes(tree)
    symbols=[]
    def walk(body:list[ast.stmt],owners:list[str]):
        for node in body:
            if isinstance(node,ast.ClassDef):
                walk(node.body,owners+[node.name])
                continue
            if not isinstance(node,(ast.FunctionDef,ast.AsyncFunctionDef)):continue
            qualified=".".join(owners+[node.name])
            methods=_endpoints(node,prefixes)
            start=min([node.lineno]+[d.lineno for d in node.decorator_list])
            snippet="\n".join(lines[node.lineno-1:min(node.end_lineno or node.lineno,node.lineno+27)])[:2000]
            signature=f"{qualified}({', '.join(a.arg for a in node.args.args)})"
            doc=ast.get_docstring(node) or ""
            tokens=tokenize(" ".join([path,qualified,signature,doc[:800],snippet]))[:250]
            symbols.append({
                "symbol_id":sha256(f"{path}:{start}:{qualified}".encode()).hexdigest()[:20],
                "path":path,"name":node.name,"qualified_name":qualified,
                "line_start":start,"line_end":node.end_lineno or node.lineno,
                "kind":"endpoint" if methods else ("method" if owners else "function"),
                "http":methods,"signature":signature,"docstring":doc[:450],
                "source_excerpt":snippet,"tokens":tokens
            })
    walk(tree.body,[])
    return symbols,None

def index_archive(data:bytes,label:str="Uploaded Python project")->dict:
    if len(data)>MAX_ARCHIVE_BYTES:raise ValueError("ZIP exceeds the 8 MB compressed upload limit")
    if not zipfile.is_zipfile(BytesIO(data)):raise ValueError("Upload a valid ZIP archive")
    symbols=[]
    warnings=[]
    seen=set()
    with zipfile.ZipFile(BytesIO(data)) as archive:
        members=archive.infolist()
        if len(members)>10000:raise ValueError("Archive contains too many entries")
        if sum(i.file_size for i in members if not i.is_dir())>MAX_TOTAL_SOURCE_BYTES:
            raise ValueError("Archive uncompressed size exceeds 24 MB")
        allowed=[]
        for info in members:
            if info.is_dir():continue
            if _is_unsafe_link(info):raise ValueError("ZIP symlinks are not allowed")
            path=_safe_member_path(info.filename)
            if path is None:
                if info.filename.endswith(".py") and (".." in PurePosixPath(info.filename).parts or info.filename.startswith("/")):
                    raise ValueError("Unsafe ZIP source path")
                continue
            if info.file_size>MAX_SOURCE_BYTES:raise ValueError(f"Source file exceeds 1 MB: {path}")
            if info.compress_size and info.file_size>info.compress_size*150:raise ValueError("Suspicious ZIP compression ratio")
            if path in seen:raise ValueError("Duplicate source filename in archive")
            seen.add(path)
            allowed.append((info,path))
        if len(allowed)>MAX_FILES:raise ValueError("Archive contains more than 400 Python source files")
        roots={p.split("/")[0] for _,p in allowed if "/" in p}
        strip=next(iter(roots)) if len(roots)==1 and all("/" in p for _,p in allowed) else None
        for info,path in allowed:
            relative=path[len(strip)+1:] if strip else path
            try:
                source_bytes=archive.read(info)
                src=source_bytes.decode("utf-8-sig")
            except (UnicodeDecodeError,RuntimeError,zipfile.BadZipFile):
                warnings.append(f"Skipped unreadable source: {relative}")
                continue
            indexed,warning=_index_python(relative,src)
            if warning:warnings.append(warning)
            # Hash exact original ZIP member bytes, not a normalized excerpt.
            # This permits M9 to check the executed image's Python module bytes.
            file_digest=sha256(source_bytes).hexdigest()
            for symbol in indexed:
                symbol["source_sha256"]=file_digest
            symbols.extend(indexed)
            if len(symbols)>MAX_SYMBOLS:raise ValueError("Archive exceeds 12,000 source symbols")
    if not symbols:raise ValueError("No parsable Python functions or FastAPI endpoints were found")
    return {
        "index_id":sha256(data).hexdigest(),"label":label.strip()[:100] or "Uploaded Python project",
        "source_type":"uploaded_zip","files_indexed":len(allowed),"symbols_indexed":len(symbols),
        "created_at":datetime.now(timezone.utc).isoformat(),"warnings":warnings[:50],"symbols":symbols,
        "methodology":"Python AST + BM25-style lexical retrieval; all links are unverified candidates"
    }

def save_index(index:dict,directory:Path)->None:
    directory.mkdir(parents=True,exist_ok=True)
    target=directory/f"{index['index_id']}.json"
    fd,temp=tempfile.mkstemp(prefix=".index-",suffix=".tmp",dir=directory)
    try:
        with os.fdopen(fd,"w",encoding="utf-8") as f:json.dump(index,f,ensure_ascii=False)
        os.replace(temp,target)
    finally:
        if os.path.exists(temp):os.unlink(temp)

def load_index(index_id:str,directory:Path)->dict:
    if not re.fullmatch(r"[a-f0-9]{64}",index_id):raise ValueError("Invalid index ID")
    path=directory/f"{index_id}.json"
    if not path.is_file():raise FileNotFoundError("Code index not found")
    content=json.loads(path.read_text(encoding="utf-8"))
    if content.get("index_id")!=index_id:raise ValueError("Index has invalid identity")
    return content

def rank_candidates(requirement_text:str,index:dict,top_k:int=5)->list[dict]:
    """Uncalibrated candidate ranking; never call results verified or implemented."""
    query=set(tokenize(requirement_text))
    if not query:return []
    symbols=index.get("symbols",[])
    if not symbols:return []
    docs=[Counter(s["tokens"]) for s in symbols]
    df=Counter(t for doc in docs for t in doc)
    N=len(docs)
    avg_len=max(1,sum(sum(d.values()) for d in docs)/N)
    ranked=[]
    for sym,doc in zip(symbols,docs):
        length=max(1,sum(doc.values()))
        overlap=sorted(query.intersection(doc))
        if not overlap:continue
        score=0.0
        features=["lexical_overlap"]
        for term in overlap:
            idf=math.log(1+(N-df[term]+0.5)/(df[term]+0.5))
            tf=doc[term]
            score+=idf*(tf*2.2)/(tf+1.2*(0.25+0.75*length/avg_len))
        route_tokens=tokenize(" ".join(e["route"] for e in sym["http"]))
        route_matches=query.intersection(route_tokens)
        if route_matches:
            score+=1.25*len(route_matches)
            features.append("api_route")
        name_matches=query.intersection(tokenize(sym["qualified_name"]))
        if name_matches:
            score+=0.85*len(name_matches)
            features.append("symbol_name")
        ranked.append({
            "symbol_id":sym["symbol_id"],"path":sym["path"],"qualified_name":sym["qualified_name"],
            "kind":sym["kind"],"line_start":sym["line_start"],"line_end":sym["line_end"],
            "http":sym["http"],"score":round(score,4),"matched_terms":overlap,"evidence_features":features,
            "signature":sym["signature"],"source_excerpt":sym["source_excerpt"],
            "verification_status":"candidate_unverified",
            "explanation":"Candidate from text and code overlap. Behavior NOT verified."
        })
    return sorted(ranked,key=lambda x:(-x["score"],x["path"],x["line_start"]))[:max(1,min(top_k,10))]
