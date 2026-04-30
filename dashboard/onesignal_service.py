"""
dashboard/onesignal_service.py
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
OneSignal REST API v1 wrapper.

Usage anywhere in the project:
    from dashboard.onesignal_service import push_to_admins, push_to_players

Config (settings.py):
    ONESIGNAL_APP_ID  = "your-app-id-uuid"
    ONESIGNAL_API_KEY = "your-rest-api-key"   # NOT the user key — the REST key
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
"""

import logging
import requests
from django.conf import settings

logger = logging.getLogger(__name__)

ONESIGNAL_URL = "https://onesignal.com/api/v1/notifications"


def _headers():
    return {
        "Content-Type": "application/json",
        "Authorization": f"Basic {settings.ONESIGNAL_API_KEY}",
    }


def _base_payload(title: str, message: str, url: str = "") -> dict:
    payload = {
        "app_id": settings.ONESIGNAL_APP_ID,
        "headings": {"en": title},
        "contents": {"en": message},
        "web_push_topic": "admin-dashboard",  # collapses duplicate topics
    }
    if url:
        payload["url"] = url
    return payload


# ── Icon / badge mapping per notification type ─────────────────
ICON_MAP = {
    "new_order":    "🛒",
    "low_stock":    "⚠️",
    "out_of_stock": "❌",
    "payment":      "💳",
    "refund":       "↩️",
    "new_user":     "👤",
    "system":       "🔔",
}


def push_to_players(
    player_ids: list[str],
    title: str,
    message: str,
    url: str = "",
    notif_type: str = "system",
) -> bool:
    """
    Send a push notification to a specific list of OneSignal player IDs.
    Returns True if the API call succeeded.
    """
    if not player_ids:
        return False

    icon = ICON_MAP.get(notif_type, "🔔")
    payload = _base_payload(f"{icon} {title}", message, url)
    payload["include_player_ids"] = player_ids

    try:
        resp = requests.post(ONESIGNAL_URL, json=payload, headers=_headers(), timeout=5)
        resp.raise_for_status()
        logger.info("Push sent to %d players: %s", len(player_ids), title)
        return True
    except requests.RequestException as exc:
        logger.warning("OneSignal push failed: %s", exc)
        return False


def push_to_admins(
    title: str,
    message: str,
    url: str = "",
    notif_type: str = "system",
) -> bool:
    """
    Send a push notification to ALL active admin / staff users who have
    registered a OneSignal player_id.
    """
    from dashboard.models import AdminPushDevice  # local import avoids circular dep

    player_ids = list(
        AdminPushDevice.objects
        .filter(is_active=True)
        .values_list("player_id", flat=True)
        .distinct()
    )

    return push_to_players(player_ids, title, message, url, notif_type)