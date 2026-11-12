from fastapi import FastAPI

from app.routes import router as tasks_router

app = FastAPI(title="Task Tracker API", version="0.1.0")
app.include_router(tasks_router)
