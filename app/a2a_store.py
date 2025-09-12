# app/a2a_store.py
import time, uuid
from typing import Dict, Any

class TaskStore:
    def __init__(self):
        self.tasks: Dict[str, Dict[str, Any]] = {}

    def new_task(self, context_id: str) -> Dict[str, Any]:
        tid = f"task_{uuid.uuid4().hex[:8]}"
        t = {
            "id": tid,
            "contextId": context_id,
            "status": {"state": "submitted"},
            "artifacts": [],
            "history": [],
            "kind": "task",
            "metadata": {}
        }
        self.tasks[tid] = t
        return t

    def get(self, tid: str) -> Dict[str, Any] | None:
        return self.tasks.get(tid)

    def update_status(self, tid: str, state: str):
        if tid in self.tasks:
            self.tasks[tid]["status"] = {"state": state}

    def add_history(self, tid: str, role: str, parts: list, message_id: str):
        if tid not in self.tasks:
            return
        self.tasks[tid]["history"].append({
            "role": role,
            "parts": parts,
            "messageId": message_id,
            "taskId": tid,
            "contextId": self.tasks[tid]["contextId"],
            "kind": "message",
            "metadata": {}
        })

STORE = TaskStore()