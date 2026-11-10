"""Read M3 progress history and present the M2 gap summary when available."""

from collections import defaultdict
from collections.abc import Callable
from datetime import UTC, date, datetime, timedelta

from sqlalchemy import select
from sqlalchemy.orm import Session

from backend.catalogue import get_resource
from backend.dashboard.schemas import (
    GapSummary,
    Milestone,
    ProgressDashboard,
    ProgressSnapshot,
    ResourceProgress,
)
from backend.progress.models import Progress, ProgressEvent
from backend.progress.schemas import ProgressOut

GapSummaryReader = Callable[[int, Session], GapSummary | None]


def get_gap_summary_reader() -> GapSummaryReader | None:
    """M2 has not published an original-versus-current gap summary."""
    return None


def _current_streak(events: list[ProgressEvent], today: date) -> int:
    active_days: set[date] = set()
    previous: dict[int, int] = {}
    for event in events:
        prior = previous.get(event.progress_id)
        if event.status == "completed" or (
            prior is not None and event.completion_percentage > prior
        ):
            active_days.add(event.occurred_at.astimezone(UTC).date())
        previous[event.progress_id] = event.completion_percentage

    day = today if today in active_days else today - timedelta(days=1)
    count = 0
    while day in active_days:
        count += 1
        day -= timedelta(days=1)
    return count


def read_dashboard(
    student_id: int, session: Session, gap_reader: GapSummaryReader | None,
) -> ProgressDashboard:
    rows = session.execute(select(Progress, ProgressEvent).outerjoin(ProgressEvent).where(
        Progress.student_id == student_id
    ).order_by(Progress.progress_id, ProgressEvent.occurred_at, ProgressEvent.event_id))
    progress_rows: dict[int, Progress] = {}
    events: list[ProgressEvent] = []
    history: dict[int, list[ProgressSnapshot]] = defaultdict(list)
    for row, event in rows:
        progress_rows[row.progress_id] = row
        if event is not None:
            events.append(event)
            history[row.progress_id].append(ProgressSnapshot.model_validate(event))

    resources = []
    for row in progress_rows.values():
        item = get_resource(row.resource_id, session)
        resources.append(ResourceProgress(
            **ProgressOut.model_validate(row).model_dump(),
            title=item["title"] if item is not None else None,
            history=history[row.progress_id],
        ))

    completed_count = sum(row.status == "completed" for row in progress_rows.values())
    first_completion = min((e.occurred_at for e in events if e.status == "completed"), default=None)
    milestones = [
        Milestone(label="First resource completed", achieved_at=first_completion)
    ] if completed_count else []
    summary = gap_reader(student_id, session) if gap_reader is not None else None
    proportion = summary.closed / summary.total if summary and summary.total else None
    return ProgressDashboard(
        resources=resources,
        completed_count=completed_count,
        current_streak_days=_current_streak(events, datetime.now(UTC).date()),
        milestones=milestones,
        gap_summary=summary,
        gap_closure_proportion=proportion,
    )
