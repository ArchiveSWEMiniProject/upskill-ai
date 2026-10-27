"""Delete resume files past their 30-day retention date (REQ-F1-18).

Run daily, e.g. from cron or a scheduled container:
    python -m backend.profile.resume_cleanup
"""

from backend.database import get_session
from backend.profile.resume import ResumeService


def main() -> int:
    session = next(get_session())
    try:
        removed = ResumeService(session).purge_expired()
        session.commit()
    finally:
        session.close()
    print(f"Deleted {removed} expired resume file(s)")
    return removed


if __name__ == "__main__":  # pragma: no cover
    main()
