from fastapi import APIRouter

from mtaa_assignment.endpoints import hello

router = APIRouter()
router.include_router(hello.router, tags=["hello"])
