from fastapi import APIRouter, Header, HTTPException
from app.core.config import settings
from app.services.stream_control import enable_stream, disable_stream

router = APIRouter(prefix="/api/stream", tags=["stream"])

def require_token(x_control_token: str | None):
    if x_control_token != settings.CONTROL_TOKEN:
        raise HTTPException(status_code=401, detail="Unauthorized")

@router.post("/on")
async def stream_on(x_control_token: str | None = Header(default=None)):
    require_token(x_control_token)
    await enable_stream()
    return {"ok": True}

@router.post("/off")
async def stream_off(x_control_token: str | None = Header(default=None)):
    require_token(x_control_token)
    await disable_stream()
    return {"ok": True}
