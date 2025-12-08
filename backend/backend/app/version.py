import os
import time

VERSION = os.getenv("APP_VERSION", "0.1.0")
GIT_SHA = os.getenv("GIT_SHA", "dev")
STARTED_AT = int(time.time())


def info() -> dict:
    return {"version": VERSION, "git_sha": GIT_SHA, "started_at": STARTED_AT}
