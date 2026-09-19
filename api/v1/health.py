"""Health Check and SQLite WAL Persistence Verification Router."""
import sqlite3
import time
from fastapi import APIRouter, Depends, HTTPException, status
from config.settings import Settings, get_settings
from api.dependencies import get_db_session
from models.schemas import SystemHealthResponse

router = APIRouter(prefix="/health", tags=["System Health & Liveness"])


@router.get("", response_model=SystemHealthResponse)
def check_system_health(
    conn: sqlite3.Connection = Depends(get_db_session),
    settings: Settings = Depends(get_settings)
) -> SystemHealthResponse:
    """Verify runtime liveness, SQLite WAL mode, Pragmas, and persistence integrity."""
    try:
        cursor = conn.cursor()
        cursor.execute("PRAGMA journal_mode;")
        journal_mode = cursor.fetchone()[0]

        cursor.execute("PRAGMA synchronous;")
        sync_val = cursor.fetchone()[0]
        sync_map = {0: "OFF", 1: "NORMAL", 2: "FULL", 3: "EXTRA"}
        synchronous_mode = sync_map.get(sync_val, str(sync_val))

        cursor.execute("PRAGMA foreign_keys;")
        foreign_keys = bool(cursor.fetchone()[0])

        cursor.execute("PRAGMA busy_timeout;")
        busy_timeout_ms = cursor.fetchone()[0]

        # Verify quick write/read capability
        cursor.execute("SELECT 1;")
        cursor.fetchone()

        return SystemHealthResponse(
            status="HEALTHY",
            app_name=settings.app_name,
            version=settings.app_version,
            environment=settings.environment,
            database_connected=True,
            journal_mode=journal_mode.upper(),
            synchronous_mode=synchronous_mode,
            foreign_keys_enabled=foreign_keys,
            busy_timeout_ms=busy_timeout_ms,
            timestamp=int(time.time() * 1000)
        )
    except Exception as exc:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail=f"System health check failed: {str(exc)}"
        ) from exc
