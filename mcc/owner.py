"""Bounded owner-record writer. No execution, dispatch or tool authorization."""
import argparse
import fcntl
import hashlib
import json
import os
import re
import secrets
from contextlib import contextmanager
from .fs import root_fd, read_at
from .model import validate

LIMIT = 2_000_000

def encoded(value):
    return json.dumps(value, sort_keys=True, separators=(",", ":"), ensure_ascii=True)

def digest(value):
    return hashlib.sha256(encoded(value).encode()).hexdigest()

def identity(value):
    if not isinstance(value,str) or not re.fullmatch(r"[a-z0-9][a-z0-9-]{0,63}",value):
        raise ValueError("Invalid exact identity")
    return value

def atomic(fd,name,value):
    data=encoded(value)
    if len(data.encode())>LIMIT:raise ValueError("History limit reached; archive explicitly")
    tmp="txn-"+secrets.token_hex(16)
    leaf=os.open(tmp,os.O_WRONLY|os.O_CREAT|os.O_EXCL|os.O_NOFOLLOW,0o600,dir_fd=fd)
    try:
        with os.fdopen(leaf,"w") as stream:
            stream.write(data);stream.flush();os.fsync(stream.fileno())
        os.replace(tmp,name,src_dir_fd=fd,dst_dir_fd=fd);os.fsync(fd)
    finally:
        try:os.unlink(tmp,dir_fd=fd)
        except FileNotFoundError:pass

def load(fd,name):
    return json.loads(read_at(fd,name,LIMIT))

@contextmanager
def locked(root):
    fd=root_fd(root)
    lock=None
    try:
        lock=os.open("owner.lock",os.O_RDWR|os.O_CREAT|os.O_NOFOLLOW,0o600,dir_fd=fd)
        info=os.fstat(lock)
        import stat
        if not stat.S_ISREG(info.st_mode) or info.st_uid!=os.getuid() or stat.S_IMODE(info.st_mode)&0o077:raise ValueError("Unsafe lock")
        fcntl.flock(lock,fcntl.LOCK_EX)
        yield fd
    finally:
        if lock is not None:os.close(lock)
        os.close(fd)

def owner_root(fd,initialize=False):
    try:marker=load(fd,"owner-root.json")
    except FileNotFoundError:
        if not initialize:raise ValueError("Owner root not initialized")
        try:prior=load(fd,"snapshot.json")
        except FileNotFoundError:prior={"schema_version":1,"projects":[]}
        if validate(prior)["projects"] or any(n.startswith("project-") for n in os.listdir(fd)):raise ValueError("New empty owner root required")
        marker={"schema_version":2,"kind":"mcc-owner-root"};atomic(fd,"owner-root.json",marker)
    if marker!={"schema_version":2,"kind":"mcc-owner-root"}:raise ValueError("Invalid owner marker")

def reject_owner_root(fd):
    try:read_at(fd,"owner-root.json",1024)
    except FileNotFoundError:return
    raise ValueError("Owner roots cannot use legacy writers")

def validate_record(p):
    try:
        fields={"schema_version","id","name","objective","status","next_step","blockers","roadmap","updated","revision","tasks","receipts"}
        if not isinstance(p,dict) or set(p)!=fields or type(p["schema_version"]) is not int or p["schema_version"]!=2:raise ValueError("Record schema")
        identity(p["id"])
        if type(p["revision"]) is not int or p["revision"]<1 or not isinstance(p["tasks"],dict) or len(p["tasks"])>100 or not isinstance(p["receipts"],dict):raise ValueError("Record revision/collections")
        validate({"schema_version":1,"projects":[{k:p[k] for k in ("id","name","objective","status","next_step","blockers","roadmap","updated")}]})
        states={"proposed","authorized","running","failed","interrupted","awaiting_review","accepted","rejected"}
        for tid,t in p["tasks"].items():
            if set(t)!={"id","revision","scope","criteria","artifact_paths","status","authorization","attempts","decisions"} or identity(tid)!=t["id"] or type(t["revision"]) is not int or t["revision"]<1 or t["status"] not in states:raise ValueError("Task contract")
            if not isinstance(t["scope"],str) or not 0<len(t["scope"])<=4000 or not isinstance(t["criteria"],list) or not 1<=len(t["criteria"])<=20 or len(set(t["criteria"]))!=len(t["criteria"]):raise ValueError("Task scope/criteria")
            for c in t["criteria"]:identity(c)
            from pathlib import PurePosixPath
            if not isinstance(t["artifact_paths"],list) or not 1<=len(t["artifact_paths"])<=20:raise ValueError("Artifact bounds")
            for path in t["artifact_paths"]:
                q=PurePosixPath(path)
                if q.is_absolute() or not q.parts or ".." in q.parts or str(q)!=path:raise ValueError("Unsafe artifact path")
            auth=t["authorization"]
            if auth is not None and (set(auth)!={"revision","operation_key","assurance"} or type(auth["revision"]) is not int or auth["revision"]!=t["revision"] or auth["assurance"]!="procedural-human-cli"):raise ValueError("Authorization invariant")
            if t["status"] in ("authorized","running","awaiting_review","accepted","rejected","failed","interrupted") and auth is None:raise ValueError("Missing authorization")
            if not isinstance(t["attempts"],list) or len(t["attempts"])>100 or not isinstance(t["decisions"],list):raise ValueError("History contract")
            seen=set()
            for a in t["attempts"]:
                if set(a)!={"id","task_revision","status","evidence"} or identity(a["id"]) in seen or type(a["task_revision"]) is not int or not 1<=a["task_revision"]<=t["revision"] or a["status"] not in states-{"proposed","authorized"} or not isinstance(a["evidence"],dict):raise ValueError("Attempt contract")
                seen.add(a["id"])
                for c,e in a["evidence"].items():
                    if c not in t["criteria"] or set(e)!={"attempt","task_revision","path","sha256","method","passed"} or e["attempt"]!=a["id"] or type(e["task_revision"]) is not int or e["task_revision"]!=a["task_revision"] or e["path"] not in t["artifact_paths"] or not re.fullmatch(r"[0-9a-f]{64}",e["sha256"]) or not isinstance(e["method"],str) or not 0<len(e["method"])<=1000 or type(e["passed"]) is not bool:raise ValueError("Evidence contract")
            if t["status"] in ("running","awaiting_review","accepted","rejected","failed","interrupted") and (not t["attempts"] or t["attempts"][-1]["status"]!=t["status"] or t["attempts"][-1]["task_revision"]!=t["revision"]):raise ValueError("Current attempt invariant")
            for d in t["decisions"]:
                if not isinstance(d,dict) or d.get("kind") not in ("authorize","accepted","rejected") or type(d.get("revision")) is not int or not 1<=d["revision"]<=t["revision"] or d.get("assurance")!="procedural-human-cli":raise ValueError("Decision contract")
                if d["kind"]=="authorize":
                    if set(d)!={"kind","revision","operation_key","assurance"}:raise ValueError("Decision fields")
                    identity(d["operation_key"])
                elif set(d)!=({"kind","revision","attempt","evidence_digest","assurance"}|({"reason"} if d["kind"]=="rejected" else set())) or d["attempt"] not in seen or not re.fullmatch(r"[0-9a-f]{64}",d["evidence_digest"]):raise ValueError("Review decision fields")
            if auth is not None:
                identity(auth["operation_key"])
                if not any(d=={"kind":"authorize",**auth} for d in t["decisions"]):raise ValueError("Missing matching authorization decision")
            for a in t["attempts"]:
                reviews=[d for d in t["decisions"] if d["kind"]!="authorize" and d["attempt"]==a["id"]]
                if len(reviews)>1 or (reviews and reviews[0]["kind"]!=a["status"]):raise ValueError("Contradictory review history")
                if a["status"] in ("awaiting_review","accepted","rejected"):
                    if set(a["evidence"])!=set(t["criteria"]) or any(not e["passed"] for e in a["evidence"].values()):raise ValueError("Review evidence invariant")
                if a["status"] in ("accepted","rejected") and not any(d["kind"]==a["status"] and d.get("attempt")==a["id"] and d["revision"]==a["task_revision"] and d.get("evidence_digest")==digest(a["evidence"]) for d in t["decisions"]):raise ValueError("Missing matching review decision")
            for d in t["decisions"]:
                if d["kind"]!="authorize":
                    a=next(a for a in t["attempts"] if a["id"]==d["attempt"])
                    if d["revision"]!=a["task_revision"] or d["evidence_digest"]!=digest(a["evidence"]):raise ValueError("Decision evidence mismatch")
                    if d["kind"]=="rejected" and (not isinstance(d["reason"],str) or not 0<len(d["reason"])<=1000):raise ValueError("Rejection reason invariant")
        for key,r in p["receipts"].items():
            if identity(key)!=r["operation_key"] or set(r)!={"project_id","revision","operation_key","request_digest"} or r["project_id"]!=p["id"] or type(r["revision"]) is not int or not 1<=r["revision"]<=p["revision"] or not re.fullmatch(r"[0-9a-f]{64}",r["request_digest"]):raise ValueError("Receipt contract")
        return p
    except (KeyError,TypeError,AttributeError,RecursionError) as e:raise ValueError("Malformed canonical owner record") from e

def records(fd):
    # Filenames form the bounded registry; creation and projection share one lock.
    names=sorted(n for n in os.listdir(fd) if n.startswith("project-") and n.endswith(".json"))
    if len(names)>200:raise ValueError("Registry limit")
    result=[]
    for name in names:
        p=validate_record(load(fd,name))
        if p.get("schema_version")!=2 or name!="project-"+identity(p["id"])+".json":raise ValueError("Registry identity mismatch")
        result.append(p)
    return result

def projection_values(existing):
    rows=[];revisions={};tasks={}
    for p in existing:
        rows.append({k:p[k] for k in ("id","name","objective","status","next_step","blockers","roadmap","updated")})
        revisions[p["id"]]=p["revision"]
        tasks[p["id"]]=[{"id":t["id"],"status":t["status"],"revision":t["revision"]} for t in p["tasks"].values()]
    history={p["id"]:list(p["tasks"].values()) for p in existing}
    if len(encoded(history).encode())>LIMIT:raise ValueError("Aggregate history limit; no canonical commit")
    snapshot=validate({"schema_version":1,"projects":rows})
    sidecar={"schema_version":2,"revisions":revisions,"tasks":tasks,"snapshot_digest":digest(snapshot)}
    if any(len(encoded(x).encode())>LIMIT for x in (snapshot,sidecar)):raise ValueError("Aggregate projection limit; no canonical commit")
    return snapshot,sidecar

def projection(fd):
    owner_root(fd)
    snapshot,sidecar=projection_values(records(fd))
    atomic(fd,"snapshot.json",snapshot)
    atomic(fd,"owner-projection.json",sidecar)
    return sidecar["revisions"]

def freshness(fd):
    current=records(fd)
    canonical={p["id"]:p["revision"] for p in current}
    history={p["id"]:list(p["tasks"].values()) for p in current}
    if len(encoded(history).encode())>LIMIT:raise ValueError("Aggregate history limit")
    snapshot=validate(load(fd,"snapshot.json"))
    if not canonical:
        try:read_at(fd,"owner-root.json",1024)
        except FileNotFoundError:return {"canonical":{},"projected":{},"tasks":{},"stale":False,"snapshot":snapshot}
        owner_root(fd)
    try:
        projected=load(fd,"owner-projection.json")
        if not isinstance(projected,dict) or set(projected)!={"schema_version","revisions","tasks","snapshot_digest"} or type(projected["schema_version"]) is not int or projected["schema_version"]!=2 or not isinstance(projected["revisions"],dict) or not isinstance(projected["tasks"],dict):raise ValueError("Malformed projection")
        for pid,rev in projected["revisions"].items():
            identity(pid)
            if type(rev) is not int or rev<1:raise ValueError("Invalid projected revision")
        for pid,ts in projected["tasks"].items():
            identity(pid)
            if not isinstance(ts,list) or len(ts)>100:raise ValueError("Invalid projected tasks")
            for t in ts:
                if not isinstance(t,dict) or set(t)!={"id","revision","status"} or type(t["revision"]) is not int or t["revision"]<1 or not isinstance(t["status"],str):raise ValueError("Invalid projected task")
                identity(t["id"])
        expected_snapshot,expected_sidecar=projection_values(current)
        stale=projected!=expected_sidecar or snapshot!=expected_snapshot
    except (OSError,ValueError,KeyError):projected={"revisions":{},"tasks":{}};stale=True
    return {"canonical":canonical,"projected":projected["revisions"],"tasks":projected["tasks"],"history":history,"stale":stale,"snapshot":snapshot}

def evidence_check(t,a,artifact_fd):
    if set(a["evidence"])!=set(t["criteria"]):raise ValueError("All exact criteria required")
    for criterion,e in a["evidence"].items():
        if e["attempt"]!=a["id"] or e["task_revision"]!=t["revision"] or not e["passed"]:raise ValueError("Stale or failing evidence")
        raw=read_at(artifact_fd,e["path"],LIMIT,private=False)
        if hashlib.sha256(raw).hexdigest()!=e["sha256"]:raise ValueError("Artifact digest changed")

def transition(p,r,human,artifact_fd):
    op=r["operation"]; payload=r["payload"]
    common={"task_id","task_revision"}
    shapes={"rename":{"name"},"checkpoint":{"next_step","blockers"},"pause":set(),"resume":set(),
            "propose":{"task_id","scope","criteria","artifact_paths"},"edit":common|{"scope"},"authorize":common,
            "start":common|{"attempt_id"},"evidence":common|{"attempt_id","criterion","path","method","passed"},
            "finish":common|{"attempt_id"},"fail":common|{"attempt_id"},"interrupt":common|{"attempt_id"},
            "accept":common|{"attempt_id","evidence_digest"},"reject":common|{"attempt_id","evidence_digest","reason"}}
    if op not in shapes or set(payload)!=shapes[op]:raise ValueError("Exact operation payload required")
    if op in ("authorize","accept","reject","resume") and not human:raise ValueError("Human procedural review interface required")
    if op=="rename":p["name"]=payload["name"];return
    if op=="checkpoint":
        if set(payload)!={"next_step","blockers"}:raise ValueError("Scoped checkpoint fields only")
        p.update(payload);return
    if op=="pause":p["status"]="paused";return
    if op=="resume":
        if p["status"]!="paused":raise ValueError("Not paused")
        p["status"]="active";return
    tid=identity(payload["task_id"])
    if op=="propose":
        if tid in p["tasks"] or len(p["tasks"])>=100:raise ValueError("Duplicate task or bound exceeded")
        if set(payload)!={"task_id","scope","criteria","artifact_paths"}:raise ValueError("Exact proposal fields required")
        if not isinstance(payload["scope"],str) or not 0<len(payload["scope"])<=4000:raise ValueError("Bounded scope required")
        criteria=payload["criteria"];paths=payload["artifact_paths"]
        if not isinstance(criteria,list) or not 1<=len(criteria)<=20 or len(set(criteria))!=len(criteria):raise ValueError("Bounded unique criteria required")
        for c in criteria:identity(c)
        if not isinstance(paths,list) or not 1<=len(paths)<=20:raise ValueError("Bounded artifact paths required")
        for path in paths:
            from pathlib import PurePosixPath
            q=PurePosixPath(path)
            if q.is_absolute() or not q.parts or ".." in q.parts or str(q)!=path:raise ValueError("Unsafe artifact path")
        p["tasks"][tid]={"id":tid,"revision":1,"scope":payload["scope"],"criteria":criteria,"artifact_paths":paths,"status":"proposed","authorization":None,"attempts":[],"decisions":[]};return
    t=p["tasks"][tid]
    if type(payload["task_revision"]) is not int or payload["task_revision"]!=t["revision"]:raise ValueError("Stale task revision")
    if op=="edit":
        if t["status"] in ("running","accepted"):raise ValueError("Cannot edit running or accepted task")
        if set(payload)!={"task_id","task_revision","scope"}:raise ValueError("Only scope edit supported")
        if not isinstance(payload["scope"],str) or not 0<len(payload["scope"])<=4000:raise ValueError("Invalid scope")
        t["scope"]=payload["scope"];t["revision"]+=1;t["authorization"]=None;t["status"]="proposed";return
    if op=="authorize":
        if t["status"] not in ("proposed","rejected","failed","interrupted"):raise ValueError("Authorization state denied")
        auth={"revision":t["revision"],"operation_key":r["operation_key"],"assurance":"procedural-human-cli"}
        t["authorization"]=auth;t["decisions"].append({"kind":"authorize",**auth});t["status"]="authorized";return
    if op=="start":
        if p["status"]!="active" or t["status"]!="authorized" or t["authorization"]["revision"]!=t["revision"]:raise ValueError("Not authorized to start")
        aid=identity(payload["attempt_id"])
        if len(t["attempts"])>=100:raise ValueError("Attempt history bound")
        if any(a["id"]==aid for a in t["attempts"]):raise ValueError("Duplicate attempt")
        t["attempts"].append({"id":aid,"task_revision":t["revision"],"status":"running","evidence":{}});t["status"]="running";return
    a=next((a for a in t["attempts"] if a["id"]==payload["attempt_id"]),None)
    if not a or a is not t["attempts"][-1] or a["task_revision"]!=t["revision"]:raise ValueError("Wrong or stale attempt")
    if op=="evidence":
        if t["status"]!="running" or a["status"]!="running":raise ValueError("Attempt not running")
        c=payload["criterion"];path=payload["path"]
        if c in a["evidence"]:raise ValueError("Evidence immutable; fail/retry with a new attempt")
        if c not in t["criteria"] or path not in t["artifact_paths"]:raise ValueError("Wrong criterion/path scope")
        raw=read_at(artifact_fd,path,LIMIT,private=False)
        if not isinstance(payload["method"],str) or not 0<len(payload["method"])<=1000 or type(payload["passed"]) is not bool:raise ValueError("Verification method/result required")
        a["evidence"][c]={"attempt":a["id"],"task_revision":t["revision"],"path":path,"sha256":hashlib.sha256(raw).hexdigest(),"method":payload["method"],"passed":payload["passed"]};return
    if op in ("finish","fail","interrupt"):
        if t["status"]!="running" or a["status"]!="running":raise ValueError("Attempt not running")
        if op=="finish":evidence_check(t,a,artifact_fd)
        state={"finish":"awaiting_review","fail":"failed","interrupt":"interrupted"}[op]
        a["status"]=state;t["status"]=state;return
    if op in ("accept","reject"):
        if t["status"]!="awaiting_review" or a["status"]!="awaiting_review":raise ValueError("Review state required")
        if op=="reject" and (not isinstance(payload["reason"],str) or not 0<len(payload["reason"])<=1000):raise ValueError("Bounded rejection reason required")
        if op=="accept":evidence_check(t,a,artifact_fd)
        if payload["evidence_digest"]!=digest(a["evidence"]):raise ValueError("Exact evidence digest required")
        state="accepted" if op=="accept" else "rejected"
        t["decisions"].append({"kind":state,"revision":t["revision"],"attempt":a["id"],"evidence_digest":digest(a["evidence"]),"assurance":"procedural-human-cli",**({"reason":payload["reason"]} if op=="reject" else {})});t["status"]=state;a["status"]=state;return
    raise ValueError("Unknown transition")

def apply(root,artifact_root,request,human=False,fault=None):
    if set(request)!={"project_id","expected_revision","operation_key","operation","payload"}:raise ValueError("Exact request envelope required")
    pid=identity(request["project_id"]);key=identity(request["operation_key"])
    if type(request["expected_revision"]) is not int or request["expected_revision"]<0:raise ValueError("Invalid expected revision")
    if not isinstance(request["payload"],dict):raise ValueError("Invalid payload")
    fingerprint=digest(request)
    with locked(root) as fd:
        owner_root(fd,initialize=request["operation"]=="create" and human)
        name="project-"+pid+".json"
        try:p=validate_record(load(fd,name))
        except FileNotFoundError:p=None
        if p:
            if p["id"]!=pid or p["schema_version"]!=2:raise ValueError("Wrong record identity")
            if key in p["receipts"]:
                receipt=p["receipts"][key]
                if receipt["request_digest"]!=fingerprint:raise ValueError("Operation key payload collision")
                projection(fd);return receipt
        expected=p["revision"] if p else 0
        if expected!=request["expected_revision"]:raise ValueError("Stale project revision")
        if p is None:
            if request["operation"]!="create" or not human:raise ValueError("Explicit human creation required")
            existing=records(fd)
            if not existing:
                try:prior=load(fd,"snapshot.json")
                except FileNotFoundError:prior={"schema_version":1,"projects":[]}
                if validate(prior)["projects"]:raise ValueError("Use a new empty dedicated owner root")
            if len(existing)>=200:raise ValueError("Registry limit")
            q=request["payload"]
            if set(q)!={"name","objective","roadmap"}:raise ValueError("Exact creation fields required")
            p={"schema_version":2,"id":pid,**q,"status":"active","next_step":"Review a bounded task","blockers":[],"updated":"revision-1","revision":0,"tasks":{},"receipts":{}}
        else:
            afd=root_fd(artifact_root)
            try:transition(p,request,human,afd)
            finally:os.close(afd)
        p["revision"]+=1;p["updated"]="revision-"+str(p["revision"])
        validate({"schema_version":1,"projects":[{k:p[k] for k in ("id","name","objective","status","next_step","blockers","roadmap","updated")}]})
        receipt={"project_id":pid,"revision":p["revision"],"operation_key":key,"request_digest":fingerprint}
        p["receipts"][key]=receipt
        validate_record(p)
        projection_values([x for x in records(fd) if x["id"]!=pid]+[p])
        if fault=="before_commit":raise RuntimeError("Injected before commit")
        atomic(fd,name,p)
        if fault=="after_commit":raise RuntimeError("Injected after commit")
        projection(fd)
        if fault=="after_projection":raise RuntimeError("Injected before reply")
        return receipt

def main():
    parser=argparse.ArgumentParser(description="Scoped owner records; no dispatch. Human review is procedural, not same-UID tamper proof.")
    parser.add_argument("--data-dir",required=True)
    parser.add_argument("--artifact-root",required=True)
    parser.add_argument("--human",action="store_true",help="Owner-observed manual review; NOT authenticated independent identity")
    parser.add_argument("command",choices=("read","apply","reconcile"))
    parser.add_argument("--project-id")
    parser.add_argument("--request-root")
    parser.add_argument("--request-file")
    args=parser.parse_args()
    if args.command=="apply":
        fd=root_fd(args.request_root)
        try:r=load(fd,args.request_file)
        finally:os.close(fd)
        out=apply(args.data_dir,args.artifact_root,r,args.human)
    else:
        with locked(args.data_dir) as fd:
            owner_root(fd)
            if args.command=="reconcile":out=projection(fd)
            else:out=validate_record(load(fd,"project-"+identity(args.project_id)+".json"))
    print(encoded(out))
if __name__=="__main__":main()
