"""Channel API endpoints."""

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel

router = APIRouter(prefix="/api/channels", tags=["channels"])


class CreateChannel(BaseModel):
    name: str
    topic: str | None = None


class UpdateTopic(BaseModel):
    topic: str


class RenameChannel(BaseModel):
    new_name: str


@router.get("")
async def get_channels(archived: bool = False, reader_id: str | None = None):
    from dataclasses import asdict

    from space.os.bridge import channels

    try:
        channels_list = channels.list_channels(archived=archived, reader_id=reader_id)
        return [asdict(ch) for ch in channels_list]
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e)) from e


@router.post("")
async def create_channel(body: CreateChannel):
    from space.os.bridge import channels

    try:
        channel = channels.create_channel(body.name, body.topic)
        return {"ok": True, "name": channel.name}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e)) from e


@router.patch("/{channel}/topic")
async def update_channel_topic(channel: str, body: UpdateTopic):
    from space.os.bridge import channels

    try:
        channels.update_topic(channel, body.topic)
        return {"ok": True}
    except ValueError as e:
        raise HTTPException(status_code=404, detail=str(e)) from e
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e)) from e


@router.patch("/{channel}")
async def rename_channel(channel: str, body: RenameChannel):
    from space.os.bridge import channels

    try:
        channels.rename_channel(channel, body.new_name)
        return {"ok": True}
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e)) from e
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e)) from e


@router.delete("/{channel}")
async def delete_channel(channel: str):
    from space.os.bridge import channels

    try:
        channels.delete_channel(channel)
        return {"ok": True}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e)) from e


@router.post("/{channel}/archive")
async def archive_channel(channel: str):
    from space.os.bridge import channels

    try:
        channels.archive_channel(channel)
        return {"ok": True}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e)) from e


@router.post("/{channel}/restore")
async def restore_channel(channel: str):
    from space.os.bridge import channels

    try:
        channels.restore_channel(channel)
        return {"ok": True}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e)) from e


@router.post("/{channel}/pin")
async def toggle_pin_channel(channel: str):
    from space.os.bridge import channels

    try:
        is_pinned = channels.toggle_pin_channel(channel)
        return {"ok": True, "pinned": is_pinned}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e)) from e


@router.post("/{channel}/read")
async def mark_channel_read(channel: str, reader_id: str):
    from space.os.bridge import channels, messaging

    try:
        channel_obj = channels.get_channel(channel)
        if not channel_obj:
            raise HTTPException(status_code=404, detail=f"Channel {channel} not found")

        messages = messaging.get_messages(channel_obj.channel_id)
        if messages:
            messaging.update_bookmark(reader_id, channel_obj.channel_id, messages[-1].message_id)

        return {"ok": True}
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e)) from e


@router.get("/{channel}/messages")
async def get_messages_endpoint(channel: str):
    from dataclasses import asdict

    from space.os.bridge import messaging

    try:
        messages = messaging.get_messages(channel)
        return [asdict(msg) for msg in messages]
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e)) from e


class SendMessage(BaseModel):
    content: str
    sender: str | None = None


@router.post("/{channel}/messages")
async def send_message(channel: str, body: SendMessage):
    from space.lib import store
    from space.os.bridge import messaging

    try:
        sender = body.sender
        if not sender:
            with store.ensure() as conn:
                row = conn.execute(
                    "SELECT identity FROM agents WHERE (model IS NULL OR model = '') AND archived_at IS NULL LIMIT 1"
                ).fetchone()
            sender = row[0] if row else "human"
        message_id = await messaging.send_message(channel, sender, body.content)
        return {"ok": True, "message_id": message_id}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e)) from e


@router.get("/{channel_name}/agents/{agent_identity}/sessions")
def get_channel_agent_sessions(channel_name: str, agent_identity: str):
    from space.lib import store
    from space.os.bridge import channels
    from space.os.spawn import agents

    channel = channels.get_channel(channel_name)
    if not channel:
        raise HTTPException(status_code=404, detail=f"Channel {channel_name} not found")

    agent = agents.get_agent(agent_identity)
    if not agent:
        raise HTTPException(status_code=404, detail=f"Agent {agent_identity} not found")

    with store.ensure() as conn:
        rows = conn.execute(
            """
            SELECT DISTINCT s.session_id, s.provider, s.model, s.first_message_at, s.last_message_at
            FROM sessions s
            JOIN spawns sp ON s.session_id = sp.session_id
            WHERE sp.channel_id = ? AND sp.agent_id = ?
            ORDER BY s.last_message_at DESC
            """,
            (channel.channel_id, agent.agent_id),
        ).fetchall()

    return [
        {
            "session_id": row[0],
            "provider": row[1],
            "model": row[2],
            "first_message_at": row[3],
            "last_message_at": row[4],
        }
        for row in rows
    ]
