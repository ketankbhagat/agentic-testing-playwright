"""Dashboard — FastAPI + SSE for real-time pipeline visualization."""
import asyncio
import json
import os
from datetime import datetime

from fastapi import FastAPI, Request
from fastapi.responses import FileResponse, JSONResponse
from fastapi.staticfiles import StaticFiles
from sse_starlette.sse import EventSourceResponse

app = FastAPI(title="QA Agent Dashboard")

events: list[dict] = []
subscribers: list[asyncio.Queue] = []
STATIC_DIR = os.path.join(os.path.dirname(__file__), "static")
ALLURE_DIR = os.path.join(os.path.dirname(__file__), "..", "allure-report")

app.mount("/static", StaticFiles(directory=STATIC_DIR), name="static")
# check_dir=False: the report only exists after the first test run
app.mount("/allure", StaticFiles(directory=ALLURE_DIR, html=True, check_dir=False), name="allure")


async def _broadcast(data: dict):
    for q in subscribers:
        await q.put(data)


@app.get("/")
async def index():
    return FileResponse(os.path.join(STATIC_DIR, "index.html"))


@app.post("/api/event")
async def post_event(request: Request):
    data = await request.json()
    data["timestamp"] = datetime.now().isoformat()
    if data.get("type") == "start":
        events.clear()  # a new pipeline run replaces the previous one
    events.append(data)
    await _broadcast(data)
    return JSONResponse({"ok": True})


@app.get("/api/events")
async def get_events():
    return JSONResponse(events)


@app.get("/api/stream")
async def stream(request: Request):
    queue: asyncio.Queue = asyncio.Queue()
    subscribers.append(queue)

    async def generate():
        try:
            for e in list(events):
                yield {"event": "message", "data": json.dumps(e)}
            while True:
                if await request.is_disconnected():
                    break
                try:
                    data = await asyncio.wait_for(queue.get(), timeout=30)
                    yield {"event": "message", "data": json.dumps(data)}
                except asyncio.TimeoutError:
                    yield {"event": "ping", "data": "{}"}
        finally:
            subscribers.remove(queue)

    return EventSourceResponse(generate())


@app.post("/api/reset")
async def reset():
    events.clear()
    await _broadcast({"type": "reset", "timestamp": datetime.now().isoformat()})
    return JSONResponse({"ok": True})
