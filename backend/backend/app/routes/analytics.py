from fastapi import APIRouter, Depends, HTTPException, Request
from fastapi.responses import StreamingResponse, Response
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from app.auth import verify_token
from app.auth.guards import require_admin
from app.db import get_conn
from app.logs.activity import stream_csv as activity_stream_csv
from datetime import datetime, timedelta

router = APIRouter(prefix="/analytics", tags=["analytics"])
security = HTTPBearer()

def _today() -> str:
    return datetime.utcnow().date().isoformat()

def _days_range(n: int) -> list[str]:
    base = datetime.utcnow().date()
    return [(base - timedelta(days=i)).isoformat() for i in range(n-1, -1, -1)]

def _get_user_ctx(creds: HTTPAuthorizationCredentials) -> dict:
    user_id = verify_token(creds.credentials)
    if not user_id:
        raise HTTPException(status_code=401, detail="Invalid token")
    # minimal user dict for guard: load email/roles from users table if present
    conn = get_conn()
    try:
        row = conn.execute("SELECT email, plan_id FROM users WHERE id=?", (user_id,)).fetchone()
        email = row[0] if row else None
        # roles not stored; default admin false unless email matches env
        user = {"id": user_id, "email": email, "roles": []}
        require_admin(user)
        return user
    finally:
        conn.close()

@router.get('/summary')
def analytics_summary(credentials: HTTPAuthorizationCredentials = Depends(security)):
    _ = _get_user_ctx(credentials)
    conn = get_conn()
    try:
        # users
        users_total = conn.execute("SELECT COUNT(1) FROM users").fetchone()[0] if conn else 0
        paying_users = conn.execute("SELECT COUNT(1) FROM users WHERE plan_id='pro'").fetchone()[0] if conn else 0
        # projects
        projects_total = 0
        try:
            projects_total = conn.execute("SELECT COUNT(1) FROM projects").fetchone()[0]
        except Exception:
            projects_total = 0
        # usage today and 7d
        today = _today()
        renders_today = 0
        tts_sec_today = 0
        try:
            row = conn.execute("SELECT SUM(renders), SUM(tts_sec) FROM usage_daily WHERE day=?", (today,)).fetchone()
            renders_today = int(row[0] or 0)
            tts_sec_today = int(row[1] or 0)
        except Exception:
            pass
        renders_7d = 0
        try:
            days = _days_range(7)
            q = "SELECT SUM(renders) FROM usage_daily WHERE day IN (%s)" % (','.join('?' for _ in days))
            r = conn.execute(q, days).fetchone()
            renders_7d = int(r[0] or 0)
        except Exception:
            pass
        # shares total
        shares_total = 0
        try:
            shares_total = conn.execute("SELECT COUNT(1) FROM shares").fetchone()[0]
        except Exception:
            shares_total = 0
        # exports
        exports_total = 0
        try:
            exports_total = conn.execute("SELECT COUNT(1) FROM exports").fetchone()[0]
        except Exception:
            exports_total = 0
        # MRR
        price = int((__import__('os').getenv('PRICE_PRO') or '9'))
        mrr = paying_users * price
        return {
            "users_total": int(users_total or 0),
            "paying_users": int(paying_users or 0),
            "projects_total": int(projects_total or 0),
            "renders_today": int(renders_today or 0),
            "renders_7d": int(renders_7d or 0),
            "tts_sec_today": int(tts_sec_today or 0),
            "exports_total": int(exports_total or 0),
            "shares_total": int(shares_total or 0),
            "mrr": int(mrr),
        }
    finally:
        conn.close()

@router.get('/timeseries/daily')
def analytics_timeseries_daily(days: int = 14, credentials: HTTPAuthorizationCredentials = Depends(security)):
    _ = _get_user_ctx(credentials)
    conn = get_conn()
    out_days = _days_range(days)
    renders = []
    tts_sec = []
    new_users = []
    exports = []
    try:
        for d in out_days:
            try:
                row = conn.execute("SELECT SUM(renders), SUM(tts_sec) FROM usage_daily WHERE day=?", (d,)).fetchone()
                renders.append(int(row[0] or 0))
                tts_sec.append(int(row[1] or 0))
            except Exception:
                renders.append(0)
                tts_sec.append(0)
            try:
                nu = conn.execute("SELECT COUNT(1) FROM users WHERE substr(created_at,1,10)=?", (d,)).fetchone()
                new_users.append(int(nu[0] or 0))
            except Exception:
                new_users.append(0)
            try:
                ex = conn.execute("SELECT COUNT(1) FROM exports WHERE substr(created_at,1,10)=?", (d,)).fetchone()
                exports.append(int(ex[0] or 0))
            except Exception:
                exports.append(0)
    finally:
        conn.close()
    return {"days": out_days, "renders": renders, "tts_sec": tts_sec, "new_users": new_users, "exports": exports}

@router.get('/audit.csv')
def analytics_audit_csv(from_day: str | None = None, to_day: str | None = None, credentials: HTTPAuthorizationCredentials = Depends(security)):
    _ = _get_user_ctx(credentials)  # also enforces admin via require_admin
    # Try reading activity log
    gen = activity_stream_csv(from_day, to_day)
    it = iter(gen)
    try:
        header = next(it)
    except StopIteration:
        header = b"timestamp,user_id,email,event,job_id,meta_json\n"
        it = iter(())
    first_data = None
    try:
        first_data = next(it)
    except StopIteration:
        first_data = None

    if first_data is None:
        # Fallback to onboarding_events
        conn = get_conn()
        try:
            try:
                cols = conn.execute("PRAGMA table_info(onboarding_events)").fetchall()
            except Exception:
                cols = []
            if not cols:
                return Response(status_code=204)
            def gen_onboarding():
                yield header
                q = "SELECT user_id, event, created_at FROM onboarding_events"
                for (uid, ev, ts) in conn.execute(q):
                    day = (ts or '')[:10]
                    if from_day and day < from_day:
                        continue
                    if to_day and day > to_day:
                        continue
                    # Map to CSV schema
                    row = [ts or '', str(uid or ''), '', ev or '', '', '{}']
                    def esc(x: str) -> str:
                        x = str(x)
                        return '"' + x.replace('"', '""') + '"'
                    yield (','.join(esc(col) for col in row) + '\n').encode('utf-8')
            return StreamingResponse(gen_onboarding(), media_type='text/csv', headers={
                'Content-Disposition': 'attachment; filename="audit.csv"'
            })
        finally:
            conn.close()
    else:
        def gen_full():
            yield header
            yield first_data
            for chunk in it:
                yield chunk
        return StreamingResponse(gen_full(), media_type='text/csv', headers={
            'Content-Disposition': 'attachment; filename="audit.csv"'
        })
