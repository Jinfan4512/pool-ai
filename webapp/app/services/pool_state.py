from dataclasses import dataclass, field
from typing import List, Tuple, Optional

Point = Tuple[int, int]

@dataclass
class PoolBoundaryState:
    detected_polygon: Optional[List[Point]] = None
    confirmed_polygon: Optional[List[Point]] = None
    boundary_set: bool = False

POOL_STATE = PoolBoundaryState()