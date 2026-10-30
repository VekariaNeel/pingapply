import sqlite3, json, time
from datetime import datetime

conn = sqlite3.connect("jobs.db", check_same_thread=False)
conn.execute("""CREATE TABLE IF NOT EXISTS jobs (
    msg_id TEXT PRIMARY KEY,
    daily_id INTEGER,
    job_date TEXT,
    job_json TEXT,
    score INTEGER,
    status TEXT,
    created_at INTEGER
)""")

# Ensure columns exist if migrating an older database
existing_cols = [col[1] for col in conn.execute("PRAGMA table_info(jobs)").fetchall()]
if "daily_id" not in existing_cols:
    conn.execute("ALTER TABLE jobs ADD COLUMN daily_id INTEGER")
if "job_date" not in existing_cols:
    conn.execute("ALTER TABLE jobs ADD COLUMN job_date TEXT")
conn.commit()

def get_today_str() -> str:
    return datetime.now().strftime("%Y-%m-%d")

def seen(msg_id: str) -> bool:
    return conn.execute("SELECT 1 FROM jobs WHERE msg_id = ?", (msg_id,)).fetchone() is not None

def get_next_daily_id(job_date: str) -> int:
    cursor = conn.execute(
        "SELECT MAX(daily_id) FROM jobs WHERE job_date = ?", (job_date,)
    )
    val = cursor.fetchone()[0]
    return (val or 0) + 1

def save(msg_id: str, job: dict, score: int, status: str, daily_id: int | None = None, job_date: str | None = None):
    if not job_date:
        job_date = get_today_str()
    conn.execute(
        "INSERT INTO jobs (msg_id, daily_id, job_date, job_json, score, status, created_at) VALUES (?, ?, ?, ?, ?, ?, ?)",
        (msg_id, daily_id, job_date, json.dumps(job), score, status, int(time.time()))
    )
    conn.commit()

def find_job_by_daily_id(daily_id: int, job_date: str | None = None) -> tuple[dict | None, str | None]:
    """
    Returns (job_data_dict, error_status).
    If found and pending: (job_data, None)
    If found and already sent: (None, "already_sent")
    If found but from older date: (None, "expired")
    If not found: (None, "not_found")
    """
    if not job_date:
        job_date = get_today_str()

    # Check today's job first
    cursor = conn.execute(
        "SELECT msg_id, job_json, score, status, daily_id, job_date FROM jobs WHERE daily_id = ? AND job_date = ?",
        (daily_id, job_date)
    )
    row = cursor.fetchone()
    if row:
        msg_id, job_json, score, status, d_id, j_date = row
        if status == "sent":
            return None, "already_sent"
        if status != "pending":
            return None, f"status_{status}"
        return {
            "msg_id": msg_id,
            "job": json.loads(job_json),
            "score": score,
            "daily_id": d_id,
            "job_date": j_date,
        }, None

    # Check if this ID existed on a previous date
    cursor_old = conn.execute(
        "SELECT msg_id, job_date FROM jobs WHERE daily_id = ? ORDER BY created_at DESC LIMIT 1",
        (daily_id,)
    )
    old_row = cursor_old.fetchone()
    if old_row:
        return None, "expired"

    return None, "not_found"

def get_latest_pending(job_date: str | None = None) -> dict | None:
    if not job_date:
        job_date = get_today_str()
    cursor = conn.execute(
        "SELECT msg_id, job_json, score, daily_id, job_date FROM jobs WHERE status = 'pending' AND job_date = ? ORDER BY daily_id DESC LIMIT 1",
        (job_date,)
    )
    row = cursor.fetchone()
    if not row:
        return None
    return {
        "msg_id": row[0],
        "job": json.loads(row[1]),
        "score": row[2],
        "daily_id": row[3],
        "job_date": row[4],
    }

def update_status(msg_id: str, status: str):
    conn.execute("UPDATE jobs SET status = ? WHERE msg_id = ?", (status, msg_id))
    conn.commit()
