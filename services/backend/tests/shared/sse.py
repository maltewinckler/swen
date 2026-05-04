"""Helpers for consuming SSE responses in integration tests."""

from __future__ import annotations

import json
from typing import Any


def read_sse_events(response) -> list[tuple[str, dict[str, Any]]]:
    events: list[tuple[str, dict[str, Any]]] = []
    current_event_type: str | None = None
    current_data: str | None = None

    for line in response.iter_lines():
        if line.startswith("event: "):
            current_event_type = line[7:]
        elif line.startswith("data: "):
            current_data = line[6:]
        elif line == "" and current_event_type and current_data:
            events.append((current_event_type, json.loads(current_data)))
            current_event_type = None
            current_data = None

    return events


def get_sse_event(
    events: list[tuple[str, dict[str, Any]]],
    event_type: str,
) -> dict[str, Any]:
    for current_event_type, data in events:
        if current_event_type == event_type:
            return data

    msg = f"Missing SSE event: {event_type}"
    raise AssertionError(msg)
