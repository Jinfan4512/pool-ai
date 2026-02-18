from fastapi import FastAPI
from fastapi.staticfiles import StaticFiles

from app.api.routes_status import router as status_router
from app.api.routes_sim import router as sim_router
from app.api.routes_stream import router as stream_router
from app.web.routes_web import router as web_router

app = FastAPI(title="Wireless Pool Safety Sensor")

app.mount("/static", StaticFiles(directory="app/web/static"), name="static")

app.include_router(web_router)
app.include_router(status_router)
app.include_router(sim_router)
app.include_router(stream_router)
