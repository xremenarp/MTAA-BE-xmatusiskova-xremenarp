from fastapi import FastAPI

from app.router import router




app = FastAPI(title="MTAA")
app.include_router(router)


import asyncio
from hypercorn.asyncio import serve
from app.config import config

asyncio.run(serve(app, config))
