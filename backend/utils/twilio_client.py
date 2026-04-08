"""
SHIELD Twilio SMS Client
─────────────────────────
Sends SMS alerts via Twilio. Gracefully falls back to logging
when credentials are not configured.
"""

import os
import logging

logger = logging.getLogger("shield.twilio")


def send_sms(to: str, score: int, top_anomalies: list[str]) -> str | None:
    """
    Send SMS alert via Twilio. Returns message SID or None if not configured.

    Args:
        to:             recipient phone number (e.g., "+919876543210")
        score:          confidence score (0–100)
        top_anomalies:  list of anomaly strings

    Returns:
        str — Twilio message SID if sent successfully
        None — if Twilio not configured or send failed
    """
    account_sid = os.getenv("TWILIO_ACCOUNT_SID")
    auth_token  = os.getenv("TWILIO_AUTH_TOKEN")
    from_number = os.getenv("TWILIO_FROM_NUMBER")

    if not all([account_sid, auth_token, from_number, to]):
        logger.warning(
            f"[TWILIO] Not configured — alert logged but not sent. "
            f"Score: {score}, Anomalies: {top_anomalies[:2]}"
        )
        return None

    # Max 2 anomalies in SMS to keep it readable
    reason_str = " | ".join(top_anomalies[:2])

    body = (
        f"[ALERT] SHIELD Alert: Suspicious activity detected.\n"
        f"Risk score: {score}/100.\n"
        f"Reason: {reason_str}.\n"
        f"Your transaction has been frozen.\n"
        f"Call 1800-SHIELD to verify."
    )

    try:
        from twilio.rest import Client
        client = Client(account_sid, auth_token)
        message = client.messages.create(body=body, from_=from_number, to=to)
        logger.info(f"[TWILIO] SMS sent to {to}: SID={message.sid}")
        return message.sid
    except Exception as e:
        logger.error(f"[TWILIO] Failed to send SMS: {e}")
        return None
