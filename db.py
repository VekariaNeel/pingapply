import sqlite3, json, time, re

conn = sqlite3.connect("jobs.db", check_same_thread=False)
conn.execute("""CREATE TABLE IF NOT EXISTS jobs (
    msg_id TEXT PRIMARY KEY,
    job_json TEXT,
    score INTEGER,
    status TEXT,
    created_at INTEGER
)""")
conn.commit()

def seen(msg_id: str) -> bool:
    return conn.execute("SELECT 1 FROM jobs WHERE msg_id = ?", (msg_id,)).fetchone() is not None

def save(msg_id: str, job: dict, score: int, status: str):
    conn.execute(
        "INSERT INTO jobs VALUES (?, ?, ?, ?, ?)",
        (msg_id, json.dumps(job), score, status, int(time.time()))
    )
    conn.commit()

def get_latest_pending() -> dict | None:
    return get_pending_job()

def get_pending_job(contact_query: str | None = None) -> dict | None:
    cursor = conn.execute(
        "SELECT msg_id, job_json, score FROM jobs WHERE status = 'pending' ORDER BY created_at DESC"
    )
    rows = cursor.fetchall()
    if not rows:
        return None

    if contact_query:
        query_digits = re.sub(r"[^\d]", "", contact_query)
        query_email = contact_query.strip().lower()

        for row in rows:
            job = json.loads(row[1])
            phone_digits = re.sub(r"[^\d]", "", job.get("contact_phone") or "")
            email = (job.get("contact_email") or "").strip().lower()

            # Match phone number suffix or email
            if (query_digits and len(query_digits) >= 6 and (query_digits in phone_digits or phone_digits in query_digits)):
                return {"msg_id": row[0], "job": job, "score": row[2]}
            if query_email and "@" in query_email and query_email in email:
                return {"msg_id": row[0], "job": job, "score": row[2]}

    # Default to the most recent pending job
    latest = rows[0]
    return {
        "msg_id": latest[0],
        "job": json.loads(latest[1]),
        "score": latest[2],
    }

def update_status(msg_id: str, status: str):
    conn.execute("UPDATE jobs SET status = ? WHERE msg_id = ?", (status, msg_id))
    conn.commit()
