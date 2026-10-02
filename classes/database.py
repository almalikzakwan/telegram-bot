import sqlite3
import os
import logging
from datetime import datetime

DB_PATH = os.path.join("storage", "hr_bot.db")


# ─── Connection ───────────────────────────────────────────────────────────────

def _connect() -> sqlite3.Connection:
    conn = sqlite3.connect(DB_PATH, check_same_thread=False)
    conn.row_factory = sqlite3.Row
    return conn


# ─── Schema initialisation ────────────────────────────────────────────────────

def init_db() -> None:
    """Create all tables if they do not yet exist."""
    with _connect() as conn:
        conn.executescript("""
            CREATE TABLE IF NOT EXISTS users (
                user_id       INTEGER PRIMARY KEY,
                full_name     TEXT    NOT NULL,
                employee_id   TEXT    NOT NULL,
                department    TEXT    NOT NULL,
                registered_at TEXT    NOT NULL
            );

            CREATE TABLE IF NOT EXISTS leave_balance (
                user_id     INTEGER NOT NULL,
                leave_type  TEXT    NOT NULL,
                total_days  INTEGER NOT NULL,
                used_days   INTEGER NOT NULL DEFAULT 0,
                PRIMARY KEY (user_id, leave_type),
                FOREIGN KEY (user_id) REFERENCES users(user_id)
            );

            CREATE TABLE IF NOT EXISTS leave_requests (
                id           INTEGER PRIMARY KEY AUTOINCREMENT,
                user_id      INTEGER NOT NULL,
                leave_type   TEXT    NOT NULL,
                dates        TEXT    NOT NULL,
                days_taken   INTEGER NOT NULL DEFAULT 1,
                mc_filename  TEXT,
                status       TEXT    NOT NULL DEFAULT 'pending',
                submitted_at TEXT    NOT NULL,
                FOREIGN KEY (user_id) REFERENCES users(user_id)
            );
        """)
    logging.info("Database initialised at %s", DB_PATH)


# ─── User operations ──────────────────────────────────────────────────────────

def is_registered(user_id: int) -> bool:
    """Return True if the user has completed registration."""
    with _connect() as conn:
        row = conn.execute(
            "SELECT 1 FROM users WHERE user_id = ?", (user_id,)
        ).fetchone()
    return row is not None


def register_user(
    user_id: int,
    full_name: str,
    employee_id: str,
    department: str,
) -> None:
    """
    Insert a new user record and initialise leave balances for all leave types.
    Uses INSERT OR REPLACE so re-registration is safe.
    """
    from .states import LEAVE_TYPES, MC_DEFAULT_DAYS

    now = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    with _connect() as conn:
        conn.execute(
            "INSERT OR REPLACE INTO users "
            "(user_id, full_name, employee_id, department, registered_at) "
            "VALUES (?, ?, ?, ?, ?)",
            (user_id, full_name, employee_id, department, now),
        )
        for key, cfg in LEAVE_TYPES.items():
            conn.execute(
                "INSERT OR IGNORE INTO leave_balance "
                "(user_id, leave_type, total_days, used_days) VALUES (?, ?, ?, 0)",
                (user_id, key, cfg["default_days"]),
            )
        # MC balance
        conn.execute(
            "INSERT OR IGNORE INTO leave_balance "
            "(user_id, leave_type, total_days, used_days) VALUES (?, 'mc', ?, 0)",
            (user_id, MC_DEFAULT_DAYS),
        )
    logging.info("Registered user %s (%s | %s | %s)", user_id, full_name, employee_id, department)


def get_user(user_id: int) -> dict | None:
    """Return the user's profile as a dict, or None if not found."""
    with _connect() as conn:
        row = conn.execute(
            "SELECT * FROM users WHERE user_id = ?", (user_id,)
        ).fetchone()
    return dict(row) if row else None


# ─── Balance operations ───────────────────────────────────────────────────────

def get_all_balances(user_id: int) -> list[dict]:
    """Return all leave balances for a user, ordered by leave type."""
    with _connect() as conn:
        rows = conn.execute(
            "SELECT leave_type, total_days, used_days "
            "FROM leave_balance WHERE user_id = ? ORDER BY leave_type",
            (user_id,),
        ).fetchall()
    return [
        {
            "leave_type": r["leave_type"],
            "total_days": r["total_days"],
            "used_days":  r["used_days"],
            "remaining":  r["total_days"] - r["used_days"],
        }
        for r in rows
    ]


def get_balance_for_type(user_id: int, leave_type: str) -> dict | None:
    """Return the balance for a single leave type, or None if not found."""
    with _connect() as conn:
        row = conn.execute(
            "SELECT total_days, used_days FROM leave_balance "
            "WHERE user_id = ? AND leave_type = ?",
            (user_id, leave_type),
        ).fetchone()
    if row is None:
        return None
    return {
        "total_days": row["total_days"],
        "used_days":  row["used_days"],
        "remaining":  row["total_days"] - row["used_days"],
    }


def deduct_balance(user_id: int, leave_type: str, days: int) -> bool:
    """
    Subtract *days* from the user's leave balance.

    Returns True on success. Returns False if the balance is insufficient
    (unpaid leave always succeeds since it has a large default quota).
    """
    with _connect() as conn:
        row = conn.execute(
            "SELECT total_days, used_days FROM leave_balance "
            "WHERE user_id = ? AND leave_type = ?",
            (user_id, leave_type),
        ).fetchone()
        if row is None:
            return False
        remaining = row["total_days"] - row["used_days"]
        if leave_type != "unpaid" and remaining < days:
            return False
        conn.execute(
            "UPDATE leave_balance SET used_days = used_days + ? "
            "WHERE user_id = ? AND leave_type = ?",
            (days, user_id, leave_type),
        )
    logging.info("Deducted %d day(s) of '%s' for user %s", days, leave_type, user_id)
    return True


# ─── Leave request operations ─────────────────────────────────────────────────

def save_leave_request(
    user_id: int,
    leave_type: str,
    dates: str,
    days_taken: int = 1,
    mc_filename: str | None = None,
) -> None:
    """Persist a submitted leave request to the database."""
    now = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    with _connect() as conn:
        conn.execute(
            "INSERT INTO leave_requests "
            "(user_id, leave_type, dates, days_taken, mc_filename, status, submitted_at) "
            "VALUES (?, ?, ?, ?, ?, 'pending', ?)",
            (user_id, leave_type, dates, days_taken, mc_filename, now),
        )
    logging.info(
        "Leave request saved: user=%s type=%s dates=%s days=%s mc=%s",
        user_id, leave_type, dates, days_taken, mc_filename,
    )


def get_leave_history(user_id: int, limit: int = 5) -> list[dict]:
    """Return the most recent *limit* leave requests for a user."""
    with _connect() as conn:
        rows = conn.execute(
            "SELECT leave_type, dates, days_taken, mc_filename, status, submitted_at "
            "FROM leave_requests WHERE user_id = ? "
            "ORDER BY submitted_at DESC LIMIT ?",
            (user_id, limit),
        ).fetchall()
    return [dict(r) for r in rows]
