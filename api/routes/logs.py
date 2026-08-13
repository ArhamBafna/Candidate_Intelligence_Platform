from fastapi import APIRouter
from config.logging import get_recent_logs

router = APIRouter(prefix="/logs", tags=["logs"])

@router.get("")
def fetch_system_logs(limit: int = 50):
    logs = get_recent_logs(limit=limit)
    has_warnings_or_errors = any(
        log.get("level") in ("warning", "error") or "warning" in log.get("event", "").lower() or "failed" in log.get("event", "").lower()
        for log in logs
    )
    return {
        "status": "warning" if has_warnings_or_errors else "normal",
        "total_buffered": len(logs),
        "logs": logs
    }
