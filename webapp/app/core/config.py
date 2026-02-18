import os

class Settings:
    # Simple shared-secret token for user actions (stream start/stop).
    # Put this in your environment later; default is fine for dev.
    CONTROL_TOKEN: str = os.getenv("CONTROL_TOKEN", "dev-token-change-me")

settings = Settings()
