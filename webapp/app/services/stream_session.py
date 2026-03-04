import secrets
from dataclasses import dataclass
from datetime import datetime, timedelta
from typing import Optional

@dataclass
class StreamSession:
    key: Optional[str] = None
    expires_at: Optional[datetime] = None

    def new_key(self, minutes: int = 30) -> str:
        self.key = secrets.token_urlsafe(24)
        self.expires_at = datetime.utcnow() + timedelta(minutes=minutes)
        return self.key

    def clear(self) -> None:
        self.key = None
        self.expires_at = None

    def is_valid(self, key: str | None) -> bool:
        if not key or not self.key or not self.expires_at:
            return False
        if key != self.key:
            return False
        return datetime.utcnow() <= self.expires_at

SESSION = StreamSession()