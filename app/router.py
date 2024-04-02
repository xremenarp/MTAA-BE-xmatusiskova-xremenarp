from fastapi import APIRouter

from app.endpoints import index

router = APIRouter()
router.include_router(index.router, tags=["hello"])
