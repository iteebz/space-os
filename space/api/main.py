"""FastAPI wrapper around CLI primitives."""

import json
import subprocess

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel

app = FastAPI(title="Space API")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:3000"],
    allow_methods=["*"],
    allow_headers=["*"],
)


def run_cli(cmd: list[str]) -> dict | list:
    result = subprocess.run(cmd, capture_output=True, text=True)
    if result.returncode != 0:
        return {"error": result.stderr.strip()}
    try:
        return json.loads(result.stdout)
    except json.JSONDecodeError:
        return {"error": "Invalid JSON response", "raw": result.stdout}


@app.get("/api/channels")
def get_channels():
    return run_cli(["bridge", "--json", "channels"])


@app.post("/api/channels")
def create_channel(body: CreateChannel):
    cmd = ["bridge", "create", body.name]
    if body.topic:
        cmd.extend(["--topic", body.topic])
    result = subprocess.run(cmd, capture_output=True, text=True)
    if result.returncode != 0:
        return {"error": result.stderr.strip()}
    return {"ok": True, "name": body.name}


@app.get("/api/channels/{channel}/messages")
def get_messages(channel: str):
    return run_cli(["bridge", "recv", channel, "--json"])


@app.get("/api/spawns")
def get_spawns():
    return run_cli(["spawn", "--json", "tasks", "--all"])


@app.get("/api/agents")
def get_agents():
    return run_cli(["spawn", "agents", "--json"])


class SendMessage(BaseModel):
    content: str
    sender: str = "human"


class CreateChannel(BaseModel):
    name: str
    topic: str | None = None


@app.post("/api/channels/{channel}/messages")
def send_message(channel: str, body: SendMessage):
    result = subprocess.run(
        ["bridge", "send", channel, body.content, "--as", body.sender],
        capture_output=True,
        text=True,
    )
    if result.returncode != 0:
        return {"error": result.stderr.strip()}
    return {"ok": True}


def main():
    import uvicorn

    uvicorn.run(app, host="0.0.0.0", port=8000, access_log=False)


if __name__ == "__main__":
    main()
