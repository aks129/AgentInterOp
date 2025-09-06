from fastapi import FastAPI
app = FastAPI()
@app.get("/hello")
def hello():
    return {"ok": True, "msg": "vercel python function is working"}