import json
from .service import purge


def run_once(dry_run: bool | None = None, older_than_days: int | None = None):
    return purge(dry_run=dry_run, older_than_days=older_than_days)


if __name__ == "__main__":
    result = run_once()
    print(json.dumps(result))
