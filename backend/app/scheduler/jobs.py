from __future__ import annotations

from datetime import datetime, timezone

from apscheduler.schedulers.asyncio import AsyncIOScheduler

from app.scheduler.notifier import notify

scheduler = AsyncIOScheduler()


async def _fire(draft_id: int, platform: str, content: str) -> None:
    await notify(draft_id, platform, content)


def schedule_draft(draft_id: int, platform: str, content: str, run_at: datetime) -> None:
    scheduler.add_job(
        _fire,
        trigger="date",
        run_date=run_at,
        args=[draft_id, platform, content],
        id=f"draft_{draft_id}",
        replace_existing=True,
    )


def reload_pending(db_session_factory) -> None:
    """Re-add scheduled jobs that survive a server restart."""
    from app.db.models import Draft

    now = datetime.now(timezone.utc).replace(tzinfo=None)
    with db_session_factory() as db:
        rows = (
            db.query(Draft)
            .filter(Draft.status == "scheduled", Draft.scheduled_at > now)
            .all()
        )
        for row in rows:
            schedule_draft(row.id, row.platform, row.content, row.scheduled_at)
