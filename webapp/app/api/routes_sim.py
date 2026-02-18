from fastapi import APIRouter
from app.services import simulation

router = APIRouter(prefix="/api/sim", tags=["simulation"])

@router.post("/boundary")
async def sim_boundary():
    await simulation.set_pool_boundary()
    return {"ok": True}

@router.post("/enter")
async def sim_enter(kind: str = "person"):
    await simulation.object_entered(kind=kind)
    return {"ok": True}

@router.post("/alive")
async def sim_alive(status: str = "alive"):
    await simulation.alive_update(status=status)
    return {"ok": True}

@router.post("/exit")
async def sim_exit():
    await simulation.object_exited()
    return {"ok": True}
