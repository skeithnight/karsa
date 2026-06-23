"""Ports (ABC interfaces) for the providers/ bounded context.

Sprint-53: AlertPort for notification delivery abstraction.
"""
from abc import ABC, abstractmethod
from typing import Dict, Any, Optional


class AlertPort(ABC):
    """Port for delivering alerts to external channels.

    Implementations: SlackAlertAdapter, EmailAlertAdapter, PagerDutyAdapter, etc.
    """

    @abstractmethod
    async def send_alert(
        self,
        title: str,
        message: str,
        severity: str = "info",
        metadata: Optional[Dict[str, Any]] = None,
    ) -> bool:
        """Send an alert to the configured channel.

        Args:
            title: Short alert title.
            message: Detailed alert message.
            severity: 'info', 'warning', 'critical'.
            metadata: Optional key-value context.

        Returns:
            True if alert was delivered successfully.
        """
        pass
