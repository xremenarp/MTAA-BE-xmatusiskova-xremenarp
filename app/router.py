"""
Router configuration module for the MTAA application.
"""


from fastapi import APIRouter
from app.auth import authentication
from app.endpoints import client
from app.endpoints import server

router = APIRouter()
router.include_router(client.router, tags=["client"])
router.include_router(server.router, tags=["server"])
router.include_router(authentication.router, tags=["auth"])
