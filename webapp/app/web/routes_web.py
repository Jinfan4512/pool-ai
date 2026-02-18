from fastapi import APIRouter, Request, WebSocket
from fastapi.responses import HTMLResponse
from fastapi.templating import Jinja2Templates
from app.services.event_bus import BUS

templates = Jinja2Templates(directory="app/web/templates")
router = APIRouter()

@router.get("/", response_class=HTMLResponse)
def home(request: Request):
    return templates.TemplateResponse("index.html", {"request": request})

@router.websocket("/ws")
async def ws_endpoint(ws: WebSocket):
    await BUS.connect(ws)
    try:
        while True:
            await ws.receive_text()
    except Exception:
        pass
    finally:
        await BUS.disconnect(ws)
