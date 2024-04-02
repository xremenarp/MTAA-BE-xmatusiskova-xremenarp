from fastapi import FastAPI

from app.router import router

app = FastAPI(title="MTAA")
app.include_router(router)
