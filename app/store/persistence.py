import os, json, sqlite3, threading
from typing import Any, Dict, List, Optional, Tuple

STORE = os.getenv("STORE", "memory").lower()
DB_PATH = os.getenv("DB_PATH", "data/agent.db")

_lock = threading.RLock()
_mem = {
    "contexts": {},   # contextId -> {scenario, config, created_at}
    "tasks": {},      # taskId -> {contextId, status, history}
    "messages": [],   # [{contextId, role, at, parts, meta}]
    "traces": {}      # contextId -> [ {ts, actor, action, detail} ]
}

def _ensure_db():
    os.makedirs(os.path.dirname(DB_PATH), exist_ok=True)
    conn = sqlite3.connect(DB_PATH)
    c = conn.cursor()
    c.execute("""create table if not exists contexts(
        id text primary key, data text, created_at text)""")
    c.execute("""create table if not exists tasks(
        id text primary key, context_id text, data text)""")
    c.execute("""create table if not exists messages(
        id integer primary key autoincrement, context_id text, role text, at text, parts text, meta text)""")
    c.execute("""create table if not exists traces(
        id integer primary key autoincrement, context_id text, ts text, actor text, action text, detail text)""")
    conn.commit(); conn.close()

if STORE == "sqlite":
    _ensure_db()

def save_context(context_id: str, data: Dict[str, Any], created_at: str):
    with _lock:
        if STORE == "sqlite":
            conn=sqlite3.connect(DB_PATH); c=conn.cursor()
            c.execute("insert or replace into contexts(id,data,created_at) values(?,?,?)",(context_id,json.dumps(data),created_at))
            conn.commit(); conn.close()
        else:
            _mem["contexts"][context_id] = {**data, "created_at": created_at}

def get_context(context_id: str) -> Optional[Dict[str, Any]]:
    with _lock:
        if STORE == "sqlite":
            conn=sqlite3.connect(DB_PATH); c=conn.cursor()
            c.execute("select data from contexts where id=?",(context_id,))
            row=c.fetchone(); conn.close()
            return json.loads(row[0]) if row else None
        else:
            return _mem["contexts"].get(context_id)

def append_message(context_id: str, role: str, at: str, parts: Any, meta: Dict[str,Any]|None=None):
    rec={"contextId":context_id,"role":role,"at":at,"parts":parts,"meta":meta or {}}
    with _lock:
        if STORE == "sqlite":
            conn=sqlite3.connect(DB_PATH); c=conn.cursor()
            c.execute("insert into messages(context_id,role,at,parts,meta) values(?,?,?,?,?)",
                      (context_id,role,at,json.dumps(parts),json.dumps(meta or {})))
            conn.commit(); conn.close()
        else:
            _mem["messages"].append(rec)

def list_messages(context_id: str) -> List[Dict[str,Any]]:
    with _lock:
        if STORE == "sqlite":
            conn=sqlite3.connect(DB_PATH); c=conn.cursor()
            c.execute("select role,at,parts,meta from messages where context_id=? order by id",(context_id,))
            rows=c.fetchall(); conn.close()
            return [{"role":r,"at":a,"parts":json.loads(p),"meta":json.loads(m)} for (r,a,p,m) in rows]
        else:
            return [m for m in _mem["messages"] if m["contextId"]==context_id]

def trace(context_id: str, ts: str, actor: str, action: str, detail: Dict[str,Any]):
    with _lock:
        if STORE == "sqlite":
            conn=sqlite3.connect(DB_PATH); c=conn.cursor()
            c.execute("insert into traces(context_id,ts,actor,action,detail) values(?,?,?,?,?)",
                      (context_id,ts,actor,action,json.dumps(detail)))
            conn.commit(); conn.close()
        else:
            _mem["traces"].setdefault(context_id,[]).append({"ts":ts,"actor":actor,"action":action,"detail":detail})

def list_traces(context_id: str) -> List[Dict[str,Any]]:
    with _lock:
        if STORE == "sqlite":
            conn=sqlite3.connect(DB_PATH); c=conn.cursor()
            c.execute("select ts,actor,action,detail from traces where context_id=? order by id",(context_id,))
            rows=c.fetchall(); conn.close()
            return [{"ts":t,"actor":a,"action":ac,"detail":json.loads(d)} for (t,a,ac,d) in rows]
        else:
            return _mem["traces"].get(context_id,[])