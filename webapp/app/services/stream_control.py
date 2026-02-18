from datetime import datetime
from app.services.state import STATE
from app.services.event_bus import BUS

async def enable_stream():
    STATE.streaming_enabled = True
    STATE.last_event = "User enabled live stream"
    STATE.last_event_time = datetime.utcnow()
    await BUS.broadcast({"type": "stream_on", "state": STATE.__dict__})

async def disable_stream():
    STATE.streaming_enabled = False
    STATE.last_event = "User disabled live stream"
    STATE.last_event_time = datetime.utcnow()
    await BUS.broadcast({"type": "stream_off", "state": STATE.__dict__})
