"""FastAPI wrapper for Space-OS APIs."""

import asyncio
import logging
import time
from contextlib import asynccontextmanager

from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware

from space.api import agents, channels, sessions, spawns, upload

logger = logging.getLogger(__name__)
START_TIME = time.time()


async def _background_sync():
    """Sync sessions in background on API startup."""
    try:
        from space.os.sessions.api import sync

        logger.info("Starting background session sync...")
        await asyncio.to_thread(sync.sync_all)
        logger.info("Background session sync complete")
    except Exception as e:
        logger.warning(f"Background session sync failed (non-fatal): {e}")


async def _timer_daemon():
    """Run timer daemon in background."""
    try:
        from space.os.bridge import timer

        logger.info("Starting timer daemon...")
        await asyncio.to_thread(timer.run)
    except Exception as e:
        logger.error(f"Timer daemon failed: {e}", exc_info=True)


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Application lifespan: startup and shutdown hooks."""
    asyncio.create_task(_background_sync())
    asyncio.create_task(_timer_daemon())
    yield


app = FastAPI(title="Space API", lifespan=lifespan)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:3000"],
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(agents.router)
app.include_router(channels.router)
app.include_router(sessions.router)
app.include_router(spawns.router)
app.include_router(upload.router)


@app.get("/api/identity")
async def get_human_identity():
    from space.lib import store

    try:
        with store.ensure() as conn:
            row = conn.execute(
                "SELECT identity FROM agents WHERE model IS NULL AND archived_at IS NULL LIMIT 1"
            ).fetchone()

        if row:
            return {"identity": row[0]}
        raise HTTPException(
            status_code=404,
            detail="No human identity configured. Run 'space init' then 'space identity set <name>'.",
        )
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e)) from e


@app.get("/api/health")
def health_check():
    from space.lib import store

    uptime_seconds = int(time.time() - START_TIME)
    db_ok = False
    db_error = None

    try:
        with store.ensure() as conn:
            conn.execute("SELECT 1").fetchone()
        db_ok = True
    except Exception as e:
        db_error = str(e)

    return {
        "uptime_seconds": uptime_seconds,
        "database": {
            "connected": db_ok,
            "error": db_error,
        },
    }


@app.delete("/api/messages/{message_id}")
async def delete_message(message_id: str):
    from space.os.bridge.api import messaging

    try:
        deleted = messaging.delete_message(message_id)
        if not deleted:
            raise HTTPException(status_code=404, detail="Message not found")
        return {"ok": True}
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e)) from e


def main():
    import uvicorn

    uvicorn.run("space.api.main:app", host="0.0.0.0", port=8000, access_log=False, reload=True)


if __name__ == "__main__":
    main()
