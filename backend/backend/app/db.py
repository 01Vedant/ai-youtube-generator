from __future__ import annotations
import sqlite3
from pathlib import Path
from typing import Iterator, Optional, Any, Dict
from typing import List

DB_PATH = Path(__file__).resolve().parents[1] / 'data' / 'app.db'
DB_PATH.parent.mkdir(parents=True, exist_ok=True)


def get_conn() -> sqlite3.Connection:
    conn = sqlite3.connect(str(DB_PATH))
    conn.row_factory = sqlite3.Row
    return conn


def init_db() -> None:
    conn = get_conn()
    try:
        # Feedback table migration
        conn.executescript(
            """
            CREATE TABLE IF NOT EXISTS user_feedback(
              id TEXT PRIMARY KEY,
              user_id TEXT,
              message TEXT NOT NULL,
              created_at TEXT NOT NULL,
              meta_json TEXT
            );
            CREATE INDEX IF NOT EXISTS idx_user_feedback_created ON user_feedback(created_at DESC);
            """
        )
        conn.execute("CREATE INDEX IF NOT EXISTS idx_shares_job_id ON shares(job_id)")
        conn.execute("CREATE INDEX IF NOT EXISTS idx_shares_user_id ON shares(user_id)")
        # Billing table
        conn.execute(
            """
            CREATE TABLE IF NOT EXISTS billing (
                user_id TEXT PRIMARY KEY,
                stripe_customer_id TEXT NOT NULL,
                stripe_sub_id TEXT NULL,
                status TEXT NOT NULL,
                current_period_end TEXT NULL
            )
            """
        )
        conn.commit()
        # Lightweight migration helpers to ensure required columns are present on legacy tables
        def column_missing(table: str, column: str) -> bool:
            cur = conn.execute(f"PRAGMA table_info({table})")
            cols = [row[1] for row in cur.fetchall()]
            return column not in cols

        # Ensure jobs_index has user_id
        try:
            if column_missing('jobs_index', 'user_id'):
                conn.execute("ALTER TABLE jobs_index ADD COLUMN user_id TEXT")
        except Exception:
            pass
        # Templates table (for user and builtin templates)
        try:
            conn.execute(
                """
                CREATE TABLE IF NOT EXISTS templates (
                    id TEXT PRIMARY KEY,
                    title TEXT NOT NULL,
                    description TEXT NULL,
                    category TEXT NULL,
                    thumb TEXT NULL,
                    plan_json TEXT NOT NULL,
                    inputs_schema TEXT NULL,
                    visibility TEXT NOT NULL DEFAULT 'private',
                    user_id TEXT NOT NULL,
                    downloads INTEGER NOT NULL DEFAULT 0,
                    created_at TEXT NOT NULL DEFAULT (strftime('%Y-%m-%dT%H:%M:%SZ','now'))
                )
                """
            )
            conn.execute("CREATE INDEX IF NOT EXISTS idx_templates_visibility ON templates(visibility)")
            conn.execute("CREATE INDEX IF NOT EXISTS idx_templates_created_at ON templates(created_at)")
            conn.execute("CREATE INDEX IF NOT EXISTS idx_templates_title ON templates(title)")
            conn.commit()
        except Exception:
            pass
        # Ensure users has plan_id
        try:
            if column_missing('users', 'plan_id'):
                conn.execute("ALTER TABLE users ADD COLUMN plan_id TEXT DEFAULT 'free'")
        except Exception:
            pass
        # Ensure jobs_index has input_json for regenerate/duplicate
        try:
            if column_missing('jobs_index', 'input_json'):
                conn.execute("ALTER TABLE jobs_index ADD COLUMN input_json TEXT")
        except Exception:
            pass
        # Ensure jobs_index has parent_job_id lineage tracking
        try:
            if column_missing('jobs_index', 'parent_job_id'):
                conn.execute("ALTER TABLE jobs_index ADD COLUMN parent_job_id TEXT")
        except Exception:
            pass
        # Ensure job_queue has lock_token and heartbeat_at
        try:
            if column_missing('job_queue', 'lock_token'):
                conn.execute("ALTER TABLE job_queue ADD COLUMN lock_token TEXT")
        except Exception:
            pass
        try:
            if column_missing('job_queue', 'heartbeat_at'):
                conn.execute("ALTER TABLE job_queue ADD COLUMN heartbeat_at TEXT")
        except Exception:
            pass
        # Ensure templates has inputs_schema column
        try:
            if column_missing('templates', 'inputs_schema'):
                conn.execute("ALTER TABLE templates ADD COLUMN inputs_schema TEXT")
        except Exception:
            pass
        try:
            if column_missing('templates', 'downloads'):
                conn.execute("ALTER TABLE templates ADD COLUMN downloads INTEGER NOT NULL DEFAULT 0")
        except Exception:
            pass
        try:
            if column_missing('templates', 'created_at'):
                conn.execute("ALTER TABLE templates ADD COLUMN created_at TEXT")
                # Backfill now for existing rows
                conn.execute("UPDATE templates SET created_at = COALESCE(created_at, strftime('%Y-%m-%dT%H:%M:%SZ','now'))")
                # Ensure indexes exist
                conn.execute("CREATE INDEX IF NOT EXISTS idx_templates_created_at ON templates(created_at)")
                conn.execute("CREATE INDEX IF NOT EXISTS idx_templates_title ON templates(title)")
                conn.commit()
        except Exception:
            pass
        # Example for exports table if it exists in some deployments
        try:
            if column_missing('exports', 'user_id'):
                conn.execute("ALTER TABLE exports ADD COLUMN user_id TEXT")
        except Exception:
            pass
        conn.commit()
        # Refresh tokens table for rotation (safe migration)
        try:
            conn.execute(
                """
                CREATE TABLE IF NOT EXISTS refresh_tokens (
                    user_id TEXT,
                    token_id TEXT PRIMARY KEY,
                    issued_at TEXT,
                    revoked_at TEXT NULL
                )
                """
            )
            conn.execute("CREATE INDEX IF NOT EXISTS idx_refresh_user ON refresh_tokens(user_id)")
            conn.commit()
        except Exception:
            pass
        # Seed plans: free, pro
        try:
            now = _utcnow_iso()
            conn.execute("INSERT OR IGNORE INTO plans (plan_id, name, created_at) VALUES (?,?,?)", ("free", "Free", now))
            conn.execute("INSERT OR IGNORE INTO plans (plan_id, name, created_at) VALUES (?,?,?)", ("pro", "Pro", now))
            conn.commit()
        except Exception:
            pass
        # Growth tables: shares_hits, referral_codes, referrals, share_unlocks
        try:
            conn.execute(
                """
                CREATE TABLE IF NOT EXISTS shares_hits (
                    share_id TEXT NOT NULL,
                    ip_hash  TEXT NOT NULL,
                    ua       TEXT NULL,
                    created_at TEXT NOT NULL,
                    UNIQUE(share_id, ip_hash, date(created_at))
                )
                """
            )
            conn.execute(
                """
                CREATE TABLE IF NOT EXISTS referral_codes (
                    code TEXT PRIMARY KEY,
                    owner_user_id TEXT NOT NULL,
                    created_at TEXT NOT NULL
                )
                """
            )
            conn.execute(
                """
                CREATE TABLE IF NOT EXISTS referrals (
                    code TEXT NOT NULL,
                    new_user_id TEXT NOT NULL,
                    created_at TEXT NOT NULL,
                    UNIQUE(code, new_user_id)
                )
                """
            )
            conn.execute(
                """
                CREATE TABLE IF NOT EXISTS share_unlocks (
                    user_id TEXT NOT NULL,
                    day TEXT NOT NULL,
                    share_id TEXT NOT NULL,
                    UNIQUE(user_id, day)
                )
                """
            )
            conn.commit()
        except Exception:
            pass
        # Onboarding events table
        try:
            conn.execute(
                """
                CREATE TABLE IF NOT EXISTS onboarding_events (
                    user_id TEXT NOT NULL,
                    event TEXT NOT NULL,
                    created_at TEXT NOT NULL,
                    UNIQUE(user_id, event)
                )
                """
            )
            conn.commit()
        except Exception:
            pass
        # Ensure waitlist table exists (redundant, safe)
        try:
            conn.executescript(
                """
                CREATE TABLE IF NOT EXISTS waitlist (
                  id TEXT PRIMARY KEY,
                  email TEXT UNIQUE,
                  created_at TEXT NOT NULL,
                  source TEXT,
                  meta_json TEXT
                );
                CREATE INDEX IF NOT EXISTS idx_waitlist_created ON waitlist(created_at DESC);
                CREATE INDEX IF NOT EXISTS idx_waitlist_email ON waitlist(email);
                """
            )
            conn.commit()
        except Exception:
            pass
    finally:
        conn.close()
    # Seed builtin templates after ensuring DB exists (idempotent)
    try:
        seed_builtin_templates()
    except Exception:
        # best effort
        pass


# =============================
# Job queue helper functions
# =============================
from datetime import datetime as _dt


def _utcnow_iso() -> str:
    return _dt.utcnow().isoformat() + "Z"


def enqueue_job(job_id: str, user_id: str, payload_json: str) -> None:
    conn = get_conn()
    try:
        now = _utcnow_iso()
        conn.execute(
            "INSERT INTO job_queue (id, user_id, payload, status, created_at, updated_at) VALUES (?,?,?,?,?,?)",
            (job_id, user_id, payload_json, 'queued', now, now),
        )
        conn.commit()
        try:
            from app.metrics import inc_renders_started  # local import to avoid import-time issues
            inc_renders_started()
        except Exception:
            pass
    finally:
        conn.close()


def dequeue_next() -> dict | None:
    conn = get_conn()
    try:
        # Use a transaction to atomically claim the next job
        conn.execute("BEGIN IMMEDIATE")
        row = conn.execute(
            "SELECT id, user_id, payload FROM job_queue WHERE status = 'queued' ORDER BY created_at ASC LIMIT 1"
        ).fetchone()
        if not row:
            conn.execute("COMMIT")
            return None
        now = _utcnow_iso()
        conn.execute(
            "UPDATE job_queue SET status='running', started_at=?, updated_at=? WHERE id=? AND status='queued'",
            (now, now, row["id"]),
        )
        conn.commit()
        return {"id": row["id"], "user_id": row["user_id"], "payload": row["payload"]}
    finally:
        conn.close()


def mark_running(job_id: str) -> None:
    conn = get_conn()
    try:
        now = _utcnow_iso()
        conn.execute(
            "UPDATE job_queue SET status='running', started_at=COALESCE(started_at, ?), updated_at=? WHERE id=?",
            (now, now, job_id),
        )
        conn.commit()
    finally:
        conn.close()

def insert_feedback(rec: Dict[str, Any]) -> None:
    conn = get_conn()
    try:
        conn.execute(
            """
            INSERT INTO user_feedback(id, user_id, message, created_at, meta_json)
            VALUES(?, ?, ?, ?, ?)
            """,
            (
                rec.get("id"),
                rec.get("user_id"),
                rec.get("message"),
                rec.get("created_at"),
                rec.get("meta_json"),
            ),
        )
        conn.commit()
    finally:
        conn.close()

def list_feedback(limit: int = 200) -> List[Dict[str, Any]]:
    conn = get_conn()
    try:
        cur = conn.execute(
            """
            SELECT id, user_id, message, created_at, meta_json
            FROM user_feedback
            ORDER BY created_at DESC
            LIMIT ?
            """,
            (limit,),
        )
        rows = cur.fetchall()
        return [
            {
                "id": r[0],
                "user_id": r[1],
                "message": r[2],
                "created_at": r[3],
                "meta_json": r[4],
            }
            for r in rows
        ]
    finally:
        conn.close()

def waitlist_add(email: str, source: Optional[str] = None, meta: Optional[Dict[str, Any]] = None) -> bool:
    """Insert waitlist entry. Returns False if duplicate."""
    conn = get_conn()
    try:
        try:
            conn.execute(
                """
                INSERT INTO waitlist(id, email, created_at, source, meta_json)
                VALUES(?, ?, strftime('%Y-%m-%dT%H:%M:%SZ','now'), ?, ?)
                """,
                (uuid_hex(), email, source, json_dumps_safe(meta)),
            )
            conn.commit()
            return True
        except sqlite3.IntegrityError:
            return False
        except Exception:
            return False
    finally:
        conn.close()

def waitlist_list(limit: int = 1000) -> List[Dict[str, Any]]:
    conn = get_conn()
    try:
        cur = conn.execute(
            """
            SELECT email, created_at, source, meta_json
            FROM waitlist
            ORDER BY created_at DESC
            LIMIT ?
            """,
            (limit,),
        )
        rows = cur.fetchall()
        return [
            {
                "email": r[0],
                "created_at": r[1],
                "source": r[2],
                "meta_json": r[3],
            }
            for r in rows
        ]
    finally:
        conn.close()

def uuid_hex() -> str:
    import uuid as _uuid
    return _uuid.uuid4().hex

def json_dumps_safe(obj: Optional[Dict[str, Any]]) -> Optional[str]:
    if obj is None:
        return None
    try:
        import json as _json
        return _json.dumps(obj)
    except Exception:
        return None


def mark_completed(job_id: str, worker_id: Optional[str] = None) -> None:
    conn = get_conn()
    try:
        now = _utcnow_iso()
        if worker_id is not None:
            conn.execute(
                "UPDATE job_queue SET status='completed', finished_at=?, updated_at=?, err_code=NULL, err_message=NULL WHERE id=? AND lock_token=?",
                (now, now, job_id, worker_id),
            )
        else:
            conn.execute(
                "UPDATE job_queue SET status='completed', finished_at=?, updated_at=?, err_code=NULL, err_message=NULL WHERE id=?",
                (now, now, job_id),
            )
        conn.commit()
        try:
            from app.metrics import inc_renders_completed
            inc_renders_completed()
        except Exception:
            pass
    finally:
        conn.close()


def mark_failed(job_id: str, code: str, msg: str, worker_id: Optional[str] = None) -> None:
    conn = get_conn()
    try:
        now = _utcnow_iso()
        if worker_id is not None:
            conn.execute(
                "UPDATE job_queue SET status='failed', finished_at=?, updated_at=?, err_code=?, err_message=? WHERE id=? AND lock_token=?",
                (now, now, code, msg, job_id, worker_id),
            )
        else:
            conn.execute(
                "UPDATE job_queue SET status='failed', finished_at=?, updated_at=?, err_code=?, err_message=? WHERE id=?",
                (now, now, code, msg, job_id),
            )
        conn.commit()
        try:
            from app.metrics import inc_renders_failed
            inc_renders_failed()
        except Exception:
            pass
    finally:
        conn.close()

def mark_cancelled(job_id: str, worker_id: Optional[str] = None, reason: str | None = None) -> None:
    conn = get_conn()
    try:
        now = _utcnow_iso()
        if worker_id is not None:
            conn.execute(
                "UPDATE job_queue SET status='cancelled', finished_at=?, updated_at=?, err_code=?, err_message=? WHERE id=? AND lock_token=?",
                (now, now, "CANCELLED", reason, job_id, worker_id),
            )
        else:
            conn.execute(
                "UPDATE job_queue SET status='cancelled', finished_at=?, updated_at=?, err_code=?, err_message=? WHERE id=?",
                (now, now, "CANCELLED", reason, job_id),
            )
        conn.commit()
    finally:
        conn.close()


def get_job_row(job_id: str) -> dict | None:
    conn = get_conn()
    try:
        row = conn.execute(
            "SELECT * FROM job_queue WHERE id = ?",
            (job_id,),
        ).fetchone()
        return dict(row) if row else None
    finally:
        conn.close()


# =============================
# Refresh token helpers
# =============================

def store_refresh(user_id: str, token_id: str, issued_at_iso: str) -> None:
    conn = get_conn()
    try:
        conn.execute(
            "INSERT OR REPLACE INTO refresh_tokens(user_id, token_id, issued_at, revoked_at) VALUES(?, ?, ?, NULL)",
            (user_id, token_id, issued_at_iso),
        )
        conn.commit()
    finally:
        conn.close()


def revoke_refresh(token_id: str, revoked_at_iso: str) -> None:
    conn = get_conn()
    try:
        conn.execute(
            "UPDATE refresh_tokens SET revoked_at=? WHERE token_id=?",
            (revoked_at_iso, token_id),
        )
        conn.commit()
    finally:
        conn.close()


def is_refresh_active(token_id: str) -> bool:
    conn = get_conn()
    try:
        row = conn.execute(
            "SELECT revoked_at FROM refresh_tokens WHERE token_id=?",
            (token_id,),
        ).fetchone()
        if not row:
            return False
        return row[0] is None
    finally:
        conn.close()


def revoke_all_for_user(user_id: str) -> None:
    conn = get_conn()
    try:
        conn.execute(
            "UPDATE refresh_tokens SET revoked_at=strftime('%Y-%m-%dT%H:%M:%SZ','now') WHERE user_id=? AND revoked_at IS NULL",
            (user_id,),
        )
        conn.commit()
    finally:
        conn.close()

# =============================
# Builtin templates seeding
# =============================
import logging as _logging

def _load_builtin_templates() -> list[dict]:
    base = Path(__file__).resolve().parent / 'templates' / 'builtin'
    if not base.exists():
        return []
    out: list[dict] = []
    for p in sorted(base.glob('*.json')):
        try:
            import json as _json
            data = _json.loads(p.read_text(encoding='utf-8'))
            # Enforce required fields
            if not data.get('id') or not data.get('title') or not data.get('plan_json'):
                continue
            data.setdefault('visibility', 'builtin')
            data.setdefault('user_id', 'system')
            out.append(data)
        except Exception:
            continue
    return out

def seed_builtin_templates() -> None:
    items = _load_builtin_templates()
    if not items:
        return
    conn = get_conn()
    try:
        loaded: list[str] = []
        for t in items:
            row = conn.execute("SELECT id FROM templates WHERE id=?", (t['id'],)).fetchone()
            if row:
                continue
            conn.execute(
                "INSERT INTO templates (id, title, description, category, thumb, plan_json, visibility, user_id) VALUES (?,?,?,?,?,?,?,?)",
                (
                    t.get('id'), t.get('title'), t.get('description'), t.get('category'), t.get('thumb'),
                    import_json_dump(t.get('plan_json')), t.get('visibility', 'builtin'), t.get('user_id', 'system')
                )
            )
            loaded.append(t['id'])
        conn.commit()
        if loaded:
            try:
                _logging.getLogger(__name__).info("Loaded builtin templates: %s", ", ".join(loaded))
            except Exception:
                pass
    finally:
        conn.close()

def import_json_dump(plan: object) -> str:
    try:
        import json as _json
        if isinstance(plan, str):
            # ensure it parses
            _json.loads(plan)
            return plan
        return _json.dumps(plan, ensure_ascii=False)
    except Exception:
        return '{}'

# =============================
# Onboarding events helpers
# =============================

def record_onboarding_event(user_id: str, event: str) -> None:
    conn = get_conn()
    try:
        now = _utcnow_iso()
        conn.execute(
            "INSERT OR IGNORE INTO onboarding_events(user_id, event, created_at) VALUES(?,?,?)",
            (user_id, event, now),
        )
        conn.commit()
    finally:
        conn.close()

def has_event(user_id: str, event: str) -> bool:
    conn = get_conn()
    try:
        row = conn.execute(
            "SELECT 1 FROM onboarding_events WHERE user_id=? AND event=?",
            (user_id, event),
        ).fetchone()
        return bool(row)
    finally:
        conn.close()


# =============================
# Crash-safe leasing API
# =============================

def lease_next(now_iso: str, worker_id: str, lease_sec: int = 300) -> dict | None:
    conn = get_conn()
    try:
        conn.execute("BEGIN IMMEDIATE")
        row = conn.execute(
            "SELECT id, user_id, payload FROM job_queue WHERE status='queued' ORDER BY created_at ASC LIMIT 1"
        ).fetchone()
        if not row:
            conn.execute("COMMIT")
            return None
        conn.execute(
            "UPDATE job_queue SET status='running', started_at=?, updated_at=?, lock_token=?, heartbeat_at=? WHERE id=? AND status='queued'",
            (now_iso, now_iso, worker_id, now_iso, row["id"]),
        )
        conn.commit()
        return {"id": row["id"], "user_id": row["user_id"], "payload": row["payload"]}
    finally:
        conn.close()


def renew_lease(job_id: str, worker_id: str, now_iso: str, extend_sec: int = 300) -> None:
    conn = get_conn()
    try:
        conn.execute(
            "UPDATE job_queue SET heartbeat_at=?, updated_at=? WHERE id=? AND lock_token=? AND status='running'",
            (now_iso, now_iso, job_id, worker_id),
        )
        conn.commit()
    finally:
        conn.close()


def requeue_stale(now_iso: str, stale_sec: int = 600) -> int:
    from datetime import datetime, timedelta
    # Compute cutoff
    cutoff = (datetime.fromisoformat(now_iso.replace("Z", "")) - timedelta(seconds=stale_sec)).isoformat() + "Z"
    conn = get_conn()
    try:
        cur = conn.execute(
            "UPDATE job_queue SET status='queued', lock_token=NULL, started_at=NULL WHERE status='running' AND heartbeat_at IS NOT NULL AND heartbeat_at < ?",
            (cutoff,),
        )
        conn.commit()
        count = cur.rowcount or 0
        try:
            from app.metrics import inc_jobs_requeued_stale
            inc_jobs_requeued_stale(count)
        except Exception:
            pass
        return count
    finally:
        conn.close()
