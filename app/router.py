from fastapi import APIRouter
from app.auth import authentification
from app.endpoints import index

router = APIRouter()
router.include_router(index.router, tags=["hello"])
router.include_router(authentification.router, tags=["auth"])
