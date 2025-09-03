"""
A2A (Agent-to-Agent) Protocol Router
"""
from fastapi import APIRouter
from pydantic import BaseModel
from app.store.memory import task_store, new_id

router = APIRouter()

class A2ATaskRequest(BaseModel):
    method: str
    params: dict = {}

class A2ATaskResponse(BaseModel):
    task_id: str
    status: str

@router.get("/tasks")
async def list_tasks():
    """Get all A2A tasks"""
    tasks = task_store.list_tasks()
    return {"tasks": [{"id": task.id, "method": task.method, "status": task.status} for task in tasks]}

@router.post("/tasks", response_model=A2ATaskResponse)
async def create_task(request: A2ATaskRequest):
    """Create a new A2A task"""
    task = task_store.create_task(request.method, request.params)
    return A2ATaskResponse(task_id=task.id, status=task.status)

@router.get("/tasks/{task_id}")
async def get_task(task_id: str):
    """Get a specific A2A task"""
    task = task_store.get_task(task_id)
    if task:
        return {"id": task.id, "method": task.method, "params": task.params, "result": task.result, "status": task.status}
    return {"error": "Task not found"}