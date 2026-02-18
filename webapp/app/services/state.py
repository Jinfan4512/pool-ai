from dataclasses import dataclass, field
from datetime import datetime
from typing import Optional, Literal

AlertLevel = Literal["none", "info", "warning", "critical"]

@dataclass
class SystemState:
    pool_boundary_set: bool = False
    object_in_pool: bool = False
    last_event: str = "System boot"
    last_event_time: datetime = field(default_factory=datetime.utcnow)

    # Alive / distress logic placeholder
    alive_status: Optional[Literal["unknown", "alive", "distress"]] = "unknown"
    alert_level: AlertLevel = "none"

    # Stream control (only user can toggle)
    streaming_enabled: bool = False

STATE = SystemState()
