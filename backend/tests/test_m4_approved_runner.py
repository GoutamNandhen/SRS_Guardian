"""M4 security boundary tests; simulated Docker CLI until an approved daemon is available."""
import asyncio
import hashlib
import json
from pathlib import Path
from subprocess import CompletedProcess
import sys
import pytest
from fastapi import FastAPI

from backend.app.research.approved_runner import (
    ApprovalError, resolve_binding, read_manifest, execute_approved, _hash, SENTINEL,
)
from backend.app.research.m4_worker import execute_request

INDEX_ID = 'a' * 64
IMAGE_ID = 'sha256:' + 'b' * 64
SYMBOL_ID = 'c' * 20
REQ = 'The system shall reject transfers exceeding 10000 rupees.'


def setup_approval(tmp_path, **changes):
    index_directory = tmp_path / 'indexes'
    index_directory.mkdir()
    index = {'index_id':INDEX_ID,'symbols':[{'symbol_id':SYMBOL_ID,'path':'banking_api.py','qualified_name':'transfer_money','http':[{'method':'POST','route':'/payments/transfer'}]}]}
    (index_directory/(INDEX_ID+'.json')).write_text(json.dumps(index))
    target = {'id':'bank-v1','approved':True,'source_index_id':INDEX_ID,'symbol_id':SYMBOL_ID,
              'image_id':IMAGE_ID,'app_module':'examples.m4.banking_api','app_attribute':'app',
              'route':'/payments/transfer','method':'POST','revision':'rev1'}
    target.update(changes)
    manifest = tmp_path/'approved_targets.json'
    manifest.write_text(json.dumps({'schema_version':'m4-approvals-1','targets':[target]}))
    return manifest,index_directory


def _fake_evidence():
    result={'target_id':'bank-v1','target_revision':'rev1','requirement_key':'REQ-1',
        'requirement_text':REQ,'endpoint':{'method':'POST','route':'/payments/transfer'},
        'decision':'passed_available_checks','cases':[{'request':{'amount':10001},'test_status':'passed'}]}
    result['evidence_sha256']=_hash(result)
    return result


def docker_stub(commands, *, evidence=None, image_override=None):
    calls=[]
    def run(argv, **kwargs):
        assert argv[0]=='docker'
        calls.append((argv,kwargs))
        assert argv[1]=='--host'
        assert argv[2].startswith(('unix://', 'npipe://'))
        if argv[3]=='image':
            return CompletedProcess(argv,0,stdout=(image_override or IMAGE_ID)+'\n',stderr='')
        return CompletedProcess(argv,0,stdout=SENTINEL+json.dumps(evidence if evidence is not None else _fake_evidence())+'\n',stderr='')
    return run,calls


def call(tmp_path,**kw):
    manifest,index_dir=setup_approval(tmp_path)
    return execute_approved(manifest_path=manifest,index_directory=index_dir,target_id='bank-v1',
        index_id=INDEX_ID,symbol_id=SYMBOL_ID,req_key='REQ-1',requirement=REQ,
        reviewer_approved=True,**kw)


def test_cli_bound_evidence_and_hardening(tmp_path):
    runner,calls=docker_stub(None)
    result=call(tmp_path,executor=runner)
    assert result['approved_source_path']=='banking_api.py'
    assert result['source_image_binding']=='operator_attested_not_cryptographically_verified'
    assert result['worker_evidence']['decision']=='passed_available_checks'
    assert len(calls)==2
    argv,_=calls[1]
    for flag in ['--network','none','--read-only','--cap-drop','ALL','--pull','never',
                 '--pids-limit','--memory','--cpus','--security-opt','no-new-privileges']:
        assert flag in argv
    assert not any(x.startswith('-v') or x.startswith('--volume') or x=='--privileged' for x in argv)
    assert 'srs-guardian.db' not in str(argv)
    assert calls[1][1]['input'].startswith('{')


def test_refuses_no_approval(tmp_path):
    manifest,index_dir=setup_approval(tmp_path)
    with pytest.raises(ApprovalError,match='mandatory'):
        execute_approved(manifest_path=manifest,index_directory=index_dir,target_id='bank-v1',index_id=INDEX_ID,symbol_id=SYMBOL_ID,
            req_key='REQ-1',requirement=REQ,reviewer_approved=False)


@pytest.mark.parametrize('change,reason',[('approved','approved'),('source_index_id','approved'),('image_id','image'),('symbol_id','Symbol'),('route','endpoint')])
def test_rejects_unapproved_or_unlinked(tmp_path,change,reason):
    val={'approved':False,'source_index_id':'d'*64,'image_id':'latest','symbol_id':'a'*20,'route':'/wrong'}[change]
    manifest,idx=setup_approval(tmp_path,**{change:val})
    with pytest.raises(ApprovalError):
        resolve_binding(manifest=read_manifest(manifest),target_id='bank-v1',index_id=INDEX_ID,symbol_id=SYMBOL_ID,index_directory=idx)


def test_refuses_wrong_image_inspection(tmp_path):
    runner,_=docker_stub(None,image_override='sha256:'+'d'*64)
    with pytest.raises(ApprovalError,match='identity mismatch'):
        call(tmp_path,executor=runner)


def test_refuses_invalid_digest(tmp_path):
    evidence=_fake_evidence()
    evidence['evidence_sha256']='x'*64
    runner,_=docker_stub(None,evidence=evidence)
    with pytest.raises(ApprovalError,match='checksum'):
        call(tmp_path,executor=runner)


def test_refuses_worker_wrong_requirement(tmp_path):
    evidence=_fake_evidence()
    evidence['requirement_key']='not-approved'
    runner,_=docker_stub(None,evidence=evidence)
    with pytest.raises(ApprovalError,match='requirement mismatch'):
        call(tmp_path,executor=runner)


def test_refuses_worker_wrong_route(tmp_path):
    evidence=_fake_evidence()
    evidence['endpoint']['route']='/stolen'
    runner,_=docker_stub(None,evidence=evidence)
    with pytest.raises(ApprovalError,match='route'):
        call(tmp_path,executor=runner)


def test_duplicate_target_ids_rejected(tmp_path):
    manifest,idx=setup_approval(tmp_path)
    data=json.loads(manifest.read_text())
    data['targets'].append(dict(data['targets'][0]))
    manifest.write_text(json.dumps(data))
    with pytest.raises(ApprovalError,match='duplicate'):
        read_manifest(manifest)


def test_worker_against_real_fastapi_asgi_in_process():
    # Docker not present here; tests actual request execution in the *worker*.
    request={'req_key':'REQ-1','requirement':REQ,'app_module':'examples.m4.banking_api',
        'app_attribute':'app','route':'/payments/transfer','target_id':'bank-v1','revision':'rev1'}
    result=execute_request(request)
    assert result['decision']=='passed_available_checks'
    assert result['target_revision']=='rev1'
    assert result['cases']
    assert result['evidence_sha256']==_hash({k:v for k,v in result.items() if k!='evidence_sha256'})


def test_worker_rejects_arbitrary_module_string():
    request={'req_key':'REQ-1','requirement':REQ,'app_module':'../../etc/passwd',
        'app_attribute':'app','route':'/payments/transfer','target_id':'bank-v1','revision':'rev1'}
    with pytest.raises(ValueError):execute_request(request)


def test_no_docker_executor_is_graceful(tmp_path):
    from subprocess import TimeoutExpired
    def missing(argv,**kwargs):raise FileNotFoundError('docker missing')
    with pytest.raises(ApprovalError,match='Docker unavailable'):
        call(tmp_path,executor=missing)
