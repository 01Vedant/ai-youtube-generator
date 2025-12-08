from __future__ import annotations

import secrets
import string


def new_share_id(length: int = 24) -> str:
    # URL-safe base62-ish: letters and digits only
    alphabet = string.ascii_letters + string.digits
    return ''.join(secrets.choice(alphabet) for _ in range(max(16, min(64, length))))
