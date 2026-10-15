"""your-first-instrument — a sense of time for a model that has none.

Why time? Ask your Claude "how long have we been talking?" WITHOUT this
connected. It can only guess: no clock lives in a context window. This
server is the smallest honest fix — and the pattern generalizes to any
instrument you can imagine. See docs/adr/ for every choice made here.
"""
import os
from datetime import datetime, timezone
from mcp.server.fastmcp import Context, FastMCP
from starlette.responses import JSONResponse

import deadline_store
from identity import current_identity

mcp = FastMCP(
    "your-first-instrument",
    host="0.0.0.0",
    port=int(os.environ.get("PORT", 8000)),
)

@mcp.tool()
def current_time() -> str:
    """The current date and time (UTC and local)."""
    now = datetime.now(timezone.utc)
    return f"UTC: {now.isoformat()} · local: {datetime.now().isoformat()}"

@mcp.tool()
def seconds_since(iso_timestamp: str) -> str:
    """Seconds elapsed since an ISO timestamp (e.g. '2026-09-10T17:15:00')."""
    then = datetime.fromisoformat(iso_timestamp)
    if then.tzinfo is None:
        then = then.replace(tzinfo=timezone.utc)
    delta = datetime.now(timezone.utc) - then
    return f"{delta.total_seconds():.0f} seconds ({delta})"

@mcp.tool()
def deadline_countdown(deadline: str) -> dict[str, str | int]:
    """Calculate time remaining until an assignment deadline, or time overdue.

    Supply an ISO 8601 date and time with an explicit UTC offset, such as
    '2026-09-25T23:59:00-04:00', or a UTC timestamp ending in Z. Ask the user
    for any missing deadline details instead of assuming a date or timezone.
    Duration fields are absolute whole days/hours/minutes/seconds; status
    distinguishes upcoming, due_now, and overdue. This reads the real clock.
    """
    timestamp = deadline.strip()
    if timestamp.endswith("Z"):
        timestamp = timestamp[:-1] + "+00:00"
    try:
        due = datetime.fromisoformat(timestamp)
    except ValueError:
        raise ValueError(
            "Invalid deadline. Use an ISO 8601 date and time with a UTC offset, "
            "for example 2026-09-25T23:59:00-04:00."
        ) from None
    if due.utcoffset() is None:
        raise ValueError(
            "Deadline must include a date, time, and timezone: use Z for UTC "
            "or an explicit offset such as -04:00."
        )

    now = datetime.now(timezone.utc)
    due_utc = due.astimezone(timezone.utc)
    status = "upcoming" if due_utc > now else "overdue" if due_utc < now else "due_now"
    distance = abs(due_utc - now)
    hours, remainder = divmod(distance.seconds, 3600)
    minutes, seconds = divmod(remainder, 60)
    duration = f"{distance.days} days, {hours} hours, {minutes} minutes, {seconds} seconds"
    if distance.days == 0 and distance.seconds == 0 and distance.microseconds:
        duration = "less than 1 second"
    if status == "due_now":
        message = "The deadline is now."
    else:
        label = "Time remaining" if status == "upcoming" else "Overdue by"
        message = f"{label}: {duration}."
    return {
        "deadline": due.isoformat(),
        "checked_at": now.isoformat(),
        "status": status,
        "days": distance.days,
        "hours": hours,
        "minutes": minutes,
        "seconds": seconds,
        "message": message,
    }

@mcp.tool()
def user_status(ctx: Context) -> dict:
    """Check identity before saving: guests share public demo deadlines; signed-in users have private lists."""
    user_id, email = current_identity(ctx)
    if user_id is None:
        return {"mode": "guest", "message": "Shared guest deadlines are visible to every guest. Sign in for a private list."}
    return {"mode": "user", "email": email, "message": "Signed in. Saved deadlines belong to your account."}


@mcp.tool()
def save_deadline(title: str, deadline: str, ctx: Context) -> dict:
    """Save an assignment and its timezone-aware deadline across conversations.

    Guests share a PUBLIC demo list. Check user_status and tell the user which
    mode they are in before saving personal information. Ask for any missing
    date, time or timezone. Signed-in callers get their own private list.
    """
    user_id, _ = current_identity(ctx)
    title = title.strip()
    if not title or len(title) > 200:
        raise ValueError("Title must contain 1 to 200 characters.")
    countdown = deadline_countdown(deadline)
    due_at = datetime.fromisoformat(str(countdown["deadline"]))
    deadline_id = deadline_store.save(user_id, title, due_at)
    return {"id": deadline_id, "title": title, "shelf": "private" if user_id else "shared guest",
            **countdown}


@mcp.tool()
def list_deadlines(ctx: Context, include_completed: bool = False) -> dict:
    """List YOUR saved assignments, earliest first, with fresh countdowns.

    Guests see the shared demo list. Completed assignments are hidden unless
    include_completed is true. Uses the real clock on every call.
    """
    user_id, _ = current_identity(ctx)
    rows = deadline_store.list_for(user_id, include_completed)
    return {"shelf": "private" if user_id else "shared guest", "deadlines": [
        {"id": str(did), "title": title, "completed": completed,
         **deadline_countdown(due_at.isoformat())}
        for did, title, due_at, completed in rows
    ]}


@mcp.tool()
def complete_deadline(deadline_id: str, ctx: Context) -> dict:
    """Mark an assignment on YOUR list complete without deleting its history.

    Use an id from list_deadlines. Other users' deadlines cannot be changed.
    """
    user_id, _ = current_identity(ctx)
    if not deadline_store.complete(user_id, deadline_id):
        return {"completed": False, "message": "No deadline with that id exists on your list."}
    return {"completed": True, "id": deadline_id}


@mcp.custom_route("/health", methods=["GET"])
async def health(request):
    return JSONResponse({"status": "ok", "service": "your-first-instrument"})


from auth import register_oauth_routes
register_oauth_routes(mcp)

if __name__ == "__main__":
    mcp.run(transport="streamable-http")
