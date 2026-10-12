"""Gotify push notifications."""

import logging

import requests

log = logging.getLogger(__name__)


def gotify(url: str, token: str, title: str, message: str, priority: int = 2) -> None:
    """Send a markdown message to a Gotify server. No-op without url and token; never raises."""
    if not url or not token:
        return
    try:
        response = requests.post(
            f"{url.rstrip('/')}/message",
            headers={"X-Gotify-Key": token},
            json={
                "title": title,
                "message": message,
                "priority": priority,
                "extras": {"client::display": {"contentType": "text/markdown"}},
            },
            timeout=10,
        )
        response.raise_for_status()
    except requests.RequestException as e:
        # str(e) can include the request URL but the token only travels in a header.
        log.warning("Gotify notification failed: %s", e)
