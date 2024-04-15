from fastapi import FastAPI
from app.router import router

app = FastAPI(title="MTAA")
app.include_router(router)

from app.config.config import config
import asyncio
from hypercorn.asyncio import serve
asyncio.run(serve(app, config))
