from typing import Optional
import threading
import numpy as np

_latest_frame: Optional[np.ndarray] = None
_lock = threading.Lock()

def set_latest_frame(frame: np.ndarray) -> None:
    global _latest_frame
    with _lock:
        _latest_frame = frame.copy()

def get_latest_frame() -> Optional[np.ndarray]:
    with _lock:
        if _latest_frame is None:
            return None
        return _latest_frame.copy()