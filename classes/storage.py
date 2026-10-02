import os
import logging
from datetime import datetime


# ─── Paths ────────────────────────────────────────────────────────────────────

STORAGE_DIR = "storage"
MC_DIR      = os.path.join(STORAGE_DIR, "mc")
LEAVES_LOG  = os.path.join(STORAGE_DIR, "leaves.log")


def ensure_dirs() -> None:
    """Create storage directories if they do not exist yet."""
    for directory in (STORAGE_DIR, MC_DIR):
        os.makedirs(directory, exist_ok=True)


# ─── Storage helpers ──────────────────────────────────────────────────────────

async def save_mc_photo(photo, user_id: int) -> str:
    """
    Download a Telegram PhotoSize object and save it to storage/mc/.

    Parameters
    ----------
    photo   : telegram.PhotoSize — highest-resolution photo from the message.
    user_id : int                — Telegram user ID, used in the filename.

    Returns
    -------
    str  — The basename of the saved file (e.g. ``mc_123456_20261001_120000.jpg``).
    """
    ensure_dirs()
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    filename  = f"mc_{user_id}_{timestamp}.jpg"
    save_path = os.path.join(MC_DIR, filename)

    tg_file = await photo.get_file()
    await tg_file.download_to_drive(save_path)

    logging.info(f"MC photo saved: {save_path} (user_id={user_id})")
    return filename


def save_leave_log(user_id: int, full_name: str, dates: str) -> None:
    """
    Append a leave request entry to storage/leaves.log.

    Parameters
    ----------
    user_id   : int — Telegram user ID.
    full_name : str — Display name of the user.
    dates     : str — Date string provided by the user.
    """
    ensure_dirs()
    now       = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    log_entry = f"[{now}] user_id={user_id} ({full_name}) | dates: {dates}\n"

    with open(LEAVES_LOG, "a", encoding="utf-8") as f:
        f.write(log_entry)

    logging.info(f"Leave log saved: {log_entry.strip()}")
