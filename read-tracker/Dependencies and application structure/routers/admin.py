from fastapi import APIRouter, Depends

from config import SettingsDep
from data import BOOKS, OPEN_SESSIONS
from dependencies import require_admin

router = APIRouter(
    prefix="/admin",
    tags=["admin"],
    dependencies=[Depends(require_admin)],
    responses={403: {"description": "Only admins can see this report."}},
)


@router.get("/readers", summary="Books per reader")
def read_reader_totals():
    """Count how many books each person has added."""
    totals = {}
    for book in BOOKS:
        totals[book["added_by"]] = totals.get(book["added_by"], 0) + 1
    return totals


@router.get("/sessions", summary="Open sessions")
def read_open_sessions():
    """Count the sessions that are open right now. When no request is running, this should be zero."""
    return {"open_sessions": len(OPEN_SESSIONS)}


@router.get("/config", summary="Current settings")
def read_config(settings: SettingsDep):
    """Show the settings the application is running with. Secret values are masked."""
    return settings.model_dump()
