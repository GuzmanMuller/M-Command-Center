import json,os,secrets,sys,tempfile,threading,time
from pathlib import Path
from mcc.fs import initialize,write_at
from mcc.owner import apply,locked,projection,freshness,digest
from mcc.server import make_server
root=Path(tempfile.mkdtemp(prefix="mcc-browser-"));data=root/"data";art=root/"art";config=root/"config"
for p in (data,art,config):fd=initialize(p);os.close(fd)
token=secrets.token_urlsafe(32);fd=os.open(config,os.O_RDONLY|os.O_DIRECTORY);write_at(fd,"auth-token",token);os.close(fd)
rev=0
req={"project_id":"reading-plan","expected_revision":0,"operation_key":"create","operation":"create","payload":{"name":"Reading plan","objective":"Synthetic browser fixture","roadmap":["Plan","Write","Review"]}}
apply(data,art,req,human=True);rev=1
server=make_server(config,data,0);threading.Thread(target=server.serve_forever,daemon=True).start()
print(json.dumps({"ready":True,"port":server.server_port,"token":token}),flush=True)
try:
    for line in sys.stdin:
        action=line.strip()
        if action=="quit":break
        if action in ("checkpoint","crash"):
            req={"project_id":"reading-plan","expected_revision":rev,"operation_key":"step-"+str(rev),"operation":"checkpoint","payload":{"next_step":"Browser automatic revision "+str(rev+1),"blockers":[]}}
            try:apply(data,art,req,fault="after_commit" if action=="crash" else None)
            except RuntimeError:pass
            rev+=1
        elif action=="history":
            def operation(op,payload,human=False):
                global rev
                apply(data,art,{"project_id":"reading-plan","expected_revision":rev,"operation_key":"ledger-"+str(rev),"operation":op,"payload":payload},human=human);rev+=1
            task={"task_id":"outline","task_revision":1}
            operation("propose",{"task_id":"outline","scope":"<img src=x onerror=alert(1)> Synthetic scope","criteria":["three-lines"],"artifact_paths":["outline.txt"]})
            for n in (1,2):
                aid="attempt-"+str(n);operation("authorize",task,True);operation("start",dict(task,attempt_id=aid))
                (art/"outline.txt").write_text("Plan\nRead\nReflect\n")
                operation("evidence",dict(task,attempt_id=aid,criterion="three-lines",path="outline.txt",method="Fixture counts three lines",passed=True))
                operation("finish",dict(task,attempt_id=aid))
                record=json.loads((data/"project-reading-plan.json").read_text());a=record["tasks"]["outline"]["attempts"][-1]
                operation("reject" if n==1 else "accept",dict(task,attempt_id=aid,evidence_digest=digest(a["evidence"]),**({"reason":"Owner requests revision"} if n==1 else {})),True)
        elif action=="reconcile":
            with locked(data) as fd:projection(fd)
        elif action=="corrupt":
            fd=os.open(data,os.O_RDONLY|os.O_DIRECTORY);write_at(fd,"snapshot.json","{}");os.close(fd)
        else:raise ValueError("Unknown fixture action")
        print("DONE "+action,flush=True)
finally:
    server.shutdown();server.server_close()
    import shutil;shutil.rmtree(root)
