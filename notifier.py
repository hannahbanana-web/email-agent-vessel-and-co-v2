"""
Notification system — SMS via Twilio + email via Gmail.
Sends urgent alerts via SMS, digests via email.
"""

import os
from twilio.rest import Client


def get_twilio_client():
    """Initialize Twilio client from env vars."""
    account_sid = os.getenv("TWILIO_ACCOUNT_SID")
    auth_token = os.getenv("TWILIO_AUTH_TOKEN")
    if not account_sid or not auth_token:
        return None
    return Client(account_sid, auth_token)


def send_sms(message: str, to: str = None):
    """Send an SMS via Twilio."""
    client = get_twilio_client()
    if not client:
        print("  [WARN] Twilio not configured — skipping SMS")
        return None

    to_number = to or os.getenv("SMS_TO_NUMBER")
    from_number = os.getenv("TWILIO_PHONE_NUMBER")

    if not to_number or not from_number:
        print("  [WARN] SMS numbers not configured — skipping")
        return None

    # Twilio SMS max is 1600 chars
    if len(message) > 1500:
        message = message[:1497] + "..."

    msg = client.messages.create(
        body=message,
        from_=from_number,
        to=to_number,
    )
    return msg.sid


def send_urgent_alert(classifications: list[dict]):
    """Send SMS for any urgent/escalated emails."""
    urgent = [
        c for c in classifications
        if c.get("priority") == "urgent" or c.get("escalation_flags")
    ]

    if not urgent:
        return

    lines = ["⚓ VESSEL AGENT — URGENT"]
    for item in urgent[:5]:  # Max 5 items per SMS
        flags = ""
        if item.get("escalation_flags"):
            flags = f" [{', '.join(item['escalation_flags'])}]"
        lines.append(f"• {item.get('from', 'Unknown')}: {item.get('subject', '')}{flags}")
        lines.append(f"  → {item.get('summary', '')}")

    if len(urgent) > 5:
        lines.append(f"  + {len(urgent) - 5} more urgent items")

    lines.append("\nCheck drafts in Gmail.")
    send_sms("\n".join(lines))


def send_scan_summary(total: int, urgent_count: int, drafts_count: int):
    """Send a brief scan completion SMS."""
    if urgent_count == 0 and total < 5:
        return  # Don't bother texting for quiet scans

    msg = (
        f"⚓ Vessel Agent scan complete\n"
        f"{total} emails processed\n"
        f"{'🔴 ' + str(urgent_count) + ' urgent' if urgent_count else '✅ Nothing urgent'}\n"
        f"{drafts_count} draft replies queued"
    )
    send_sms(msg)


def send_digest_email(gmail_service, digest_text: str, to: str = None):
    """Email the digest via Gmail."""
    import base64
    from email.mime.text import MIMEText

    recipient = to or os.getenv("DIGEST_RECIPIENTS", "hannahspatten@gmail.com")

    message = MIMEText(digest_text)
    message["to"] = recipient
    message["subject"] = f"⚓ Vessel & Co — Inbox Digest"

    raw = base64.urlsafe_b64encode(message.as_bytes()).decode()
    body = {"raw": raw}

    try:
        gmail_service.users().messages().send(userId="me", body=body).execute()
        print(f"  ✓ Digest emailed to {recipient}")
    except Exception as e:
        print(f"  [ERROR] Failed to email digest: {e}")
