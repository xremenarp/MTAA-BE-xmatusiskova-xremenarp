from fastapi import APIRouter
from app.auth import authentification
from app.endpoints import client
from app.endpoints import server

router = APIRouter()
router.include_router(client.router, tags=["client"])
router.include_router(server.router, tags=["server"])
router.include_router(authentification.router, tags=["auth"])
