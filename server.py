"""your-first-instrument — a sense of time for a model that has none.

Why time? Ask your Claude "how long have we been talking?" WITHOUT this
connected. It can only guess: no clock lives in a context window. This
server is the smallest honest fix — and the pattern generalizes to any
instrument you can imagine. See docs/adr/ for every choice made here.
"""
import os
from datetime import datetime, timezone
from mcp.server.fastmcp import FastMCP

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

if __name__ == "__main__":
    mcp.run(transport="streamable-http")
