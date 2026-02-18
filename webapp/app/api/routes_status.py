from fastapi import APIRouter
from app.services.state import STATE

router = APIRouter(prefix="/api", tags=["status"])

@router.get("/status")
def get_status():
    return {"state": STATE.__dict__}
