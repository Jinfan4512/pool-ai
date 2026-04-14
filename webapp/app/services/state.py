from dataclasses import dataclass
from datetime import datetime
from typing import Optional


@dataclass
class AppState:
    pool_boundary_set: bool = False
    object_in_pool: bool = False
    alive_status: str = "unknown"
    streaming_enabled: bool = False
    alert_level: str = "none"
    last_event: str = "System initialized"
    last_event_time: Optional[datetime] = None


STATE = AppState()