"""Slack webhook alert adapter.

Sprint-53: Sends structured alerts to a Slack channel via webhook.
"""
import logging
from typing import Dict, Any, Optional

import httpx

from karsa.providers.ports import AlertPort

logger = logging.getLogger(__name__)

SEVERITY_EMOJI = {
    "info": ":information_source:",
    "warning": ":warning:",
    "critical": ":rotating_light:",
}


class SlackAlertAdapter(AlertPort):
    """Sends alerts to Slack via incoming webhook URL."""

    def __init__(self, webhook_url: str):
        self._webhook_url = webhook_url

    async def send_alert(
        self,
        title: str,
        message: str,
        severity: str = "info",
        metadata: Optional[Dict[str, Any]] = None,
    ) -> bool:
        emoji = SEVERITY_EMOJI.get(severity, ":bell:")
        blocks = [
            {
                "type": "header",
                "text": {"type": "plain_text", "text": f"{emoji} {title}"},
            },
            {
                "type": "section",
                "text": {"type": "mrkdwn", "text": message},
            },
        ]
        if metadata:
            fields = [
                {"type": "mrkdwn", "text": f"*{k}:* {v}"}
                for k, v in metadata.items()
            ]
            blocks.append({"type": "section", "fields": fields[:10]})  # Slack limit

        payload = {"blocks": blocks}

        try:
            async with httpx.AsyncClient(timeout=10.0) as client:
                resp = await client.post(self._webhook_url, json=payload)
                if resp.status_code == 200:
                    logger.info(f"Slack alert sent: {title}")
                    return True
                else:
                    logger.error(f"Slack alert failed ({resp.status_code}): {resp.text}")
                    return False
        except Exception as e:
            logger.error(f"Slack alert error: {e}")
            return False
