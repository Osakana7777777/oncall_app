import json
import os
import sqlite3
import threading
import datetime as _dt
from pathlib import Path
from typing import List, Dict, Any, Optional

_DB_PATH = Path(os.environ.get("SURVEY_DB_PATH", Path(__file__).parent.parent / "data" / "survey.db"))
_lock = threading.Lock()


def _connect() -> sqlite3.Connection:
    _DB_PATH.parent.mkdir(parents=True, exist_ok=True)
    conn = sqlite3.connect(str(_DB_PATH))
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA foreign_keys = ON")
    return conn


def init_db() -> None:
    with _lock, _connect() as conn:
        conn.executescript(
            """
            CREATE TABLE IF NOT EXISTS surveys (
                id TEXT PRIMARY KEY,
                title TEXT NOT NULL,
                year INTEGER NOT NULL,
                month INTEGER NOT NULL,
                docs TEXT NOT NULL,
                gap_lo INTEGER NOT NULL DEFAULT 5,
                gap_hi INTEGER NOT NULL DEFAULT 8,
                created_at TEXT NOT NULL
            );
            CREATE TABLE IF NOT EXISTS survey_responses (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                survey_id TEXT NOT NULL,
                doctor TEXT NOT NULL,
                blocked TEXT NOT NULL,
                submitted_at TEXT NOT NULL,
                FOREIGN KEY (survey_id) REFERENCES surveys(id) ON DELETE CASCADE
            );
            CREATE INDEX IF NOT EXISTS idx_responses_survey ON survey_responses(survey_id);
            """
        )


def create_survey(
    survey_id: str,
    title: str,
    year: int,
    month: int,
    docs: List[str],
    gap_lo: int,
    gap_hi: int,
) -> None:
    with _lock, _connect() as conn:
        conn.execute(
            "INSERT INTO surveys (id, title, year, month, docs, gap_lo, gap_hi, created_at) "
            "VALUES (?, ?, ?, ?, ?, ?, ?, ?)",
            (
                survey_id,
                title,
                year,
                month,
                json.dumps(docs, ensure_ascii=False),
                gap_lo,
                gap_hi,
                _dt.datetime.utcnow().isoformat(timespec="seconds"),
            ),
        )


def get_survey(survey_id: str) -> Optional[Dict[str, Any]]:
    with _connect() as conn:
        row = conn.execute(
            "SELECT * FROM surveys WHERE id = ?", (survey_id,)
        ).fetchone()
    if not row:
        return None
    return {
        "id": row["id"],
        "title": row["title"],
        "year": row["year"],
        "month": row["month"],
        "docs": json.loads(row["docs"]),
        "gap_lo": row["gap_lo"],
        "gap_hi": row["gap_hi"],
        "created_at": row["created_at"],
    }


def list_surveys() -> List[Dict[str, Any]]:
    with _connect() as conn:
        rows = conn.execute(
            "SELECT s.*, "
            "  (SELECT COUNT(*) FROM survey_responses r WHERE r.survey_id = s.id) AS response_count "
            "FROM surveys s ORDER BY s.created_at DESC"
        ).fetchall()
    return [
        {
            "id": r["id"],
            "title": r["title"],
            "year": r["year"],
            "month": r["month"],
            "docs": json.loads(r["docs"]),
            "gap_lo": r["gap_lo"],
            "gap_hi": r["gap_hi"],
            "created_at": r["created_at"],
            "response_count": r["response_count"],
        }
        for r in rows
    ]


def upsert_response(survey_id: str, doctor: str, blocked: List[str]) -> None:
    with _lock, _connect() as conn:
        conn.execute(
            "DELETE FROM survey_responses WHERE survey_id = ? AND doctor = ?",
            (survey_id, doctor),
        )
        conn.execute(
            "INSERT INTO survey_responses (survey_id, doctor, blocked, submitted_at) "
            "VALUES (?, ?, ?, ?)",
            (
                survey_id,
                doctor,
                json.dumps(blocked, ensure_ascii=False),
                _dt.datetime.utcnow().isoformat(timespec="seconds"),
            ),
        )


def get_response(survey_id: str, doctor: str) -> Optional[Dict[str, Any]]:
    with _connect() as conn:
        row = conn.execute(
            "SELECT * FROM survey_responses WHERE survey_id = ? AND doctor = ?",
            (survey_id, doctor),
        ).fetchone()
    if not row:
        return None
    return {
        "doctor": row["doctor"],
        "blocked": json.loads(row["blocked"]),
        "submitted_at": row["submitted_at"],
    }


def list_responses(survey_id: str) -> List[Dict[str, Any]]:
    with _connect() as conn:
        rows = conn.execute(
            "SELECT * FROM survey_responses WHERE survey_id = ? ORDER BY doctor",
            (survey_id,),
        ).fetchall()
    return [
        {
            "doctor": r["doctor"],
            "blocked": json.loads(r["blocked"]),
            "submitted_at": r["submitted_at"],
        }
        for r in rows
    ]


def delete_survey(survey_id: str) -> bool:
    with _lock, _connect() as conn:
        cur = conn.execute("DELETE FROM surveys WHERE id = ?", (survey_id,))
        return cur.rowcount > 0
