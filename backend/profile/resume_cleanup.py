"""Delete resume files past their 30-day retention date (REQ-F1-18).

The API runs this itself, at startup and then every
RESUME_CLEANUP_INTERVAL_SECONDS (default one hour; 0 turns it off), so no
cron job has to be set up for files to be deleted. It can also be run by hand:
    python -m backend.profile.resume_cleanup
"""

import asyncio
import logging
import os

from backend.database import get_session
from backend.profile.resume import ResumeService

logger = logging.getLogger(__name__)

DEFAULT_INTERVAL_SECONDS = 3600


def interval_seconds() -> float:
    return float(os.environ.get("RESUME_CLEANUP_INTERVAL_SECONDS", DEFAULT_INTERVAL_SECONDS))


def purge_once() -> int:
    session = next(get_session())
    try:
        removed = ResumeService(session).purge_expired()
        session.commit()
    finally:
        session.close()
    return removed


async def purge_periodically(interval: float) -> None:
    """Purge now and then every `interval` seconds until cancelled. A failed run
    is logged and retried next time; it never stops the API. Purging is
    idempotent, so several API workers doing it at once is harmless."""
    while True:
        try:
            removed = await asyncio.to_thread(purge_once)
            if removed:
                logger.info("Deleted %d expired resume file(s)", removed)
        except Exception:
            logger.exception("Resume cleanup failed; retrying in %s seconds", interval)
        await asyncio.sleep(interval)


def main() -> int:
    removed = purge_once()
    print(f"Deleted {removed} expired resume file(s)")
    return removed


if __name__ == "__main__":  # pragma: no cover
    main()
