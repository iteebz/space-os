"""FastAPI wrapper for Space-OS APIs."""

import time

from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware

app = FastAPI(title="Space API")
START_TIME = time.time()

app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:3000"],
    allow_methods=["*"],
    allow_headers=["*"],
)


from space.api import agents, channels, sessions, spawns, upload

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
