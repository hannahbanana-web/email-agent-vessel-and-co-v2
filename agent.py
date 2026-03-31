"""
Vessel & Co Gmail Agent — Main runner.
Scans inbox, classifies emails, applies labels, drafts replies, generates digest.

Usage:
    python agent.py              # Run once
    python agent.py --schedule   # Run on hourly loop
    python agent.py --digest     # Generate digest only from last scan
"""

import os
import sys
import json
import base64
import argparse
from datetime import datetime, timedelta

import anthropic
import schedule
import time
from dotenv import load_dotenv
from rich.console import Console
from rich.table import Table
from rich.panel import Panel

from gmail_auth import get_gmail_service, ensure_labels_exist, apply_label, create_draft
from classifier import classify_batch
from drafter import generate_draft_reply
from digest import generate_digest, save_digest
from notifier import send_urgent_alert, send_scan_summary, send_digest_email
from config import EMAIL_CATEGORIES

load_dotenv()
console = Console()

# ─── State tracking ──────────────────────────────────────────────────
STATE_FILE = "agent_state.json"


def load_state() -> dict:
    if os.path.exists(STATE_FILE):
        with open(STATE_FILE) as f:
            return json.load(f)
    return {"last_scan": None, "processed_ids": []}


def save_state(state: dict):
    with open(STATE_FILE, "w") as f:
        json.dump(state, f, indent=2, default=str)


# ─── Email fetching ──────────────────────────────────────────────────

def fetch_new_emails(service, since: str = None, max_results: int = 50) -> list[dict]:
    """Fetch inbox emails since last scan."""
    query = "is:inbox"
    if since:
        query += f" after:{since}"

    results = service.users().messages().list(
        userId="me", q=query, maxResults=max_results
    ).execute()

    messages = results.get("messages", [])
    emails = []

    for msg_ref in messages:
        msg = service.users().messages().get(
            userId="me", id=msg_ref["id"], format="full"
        ).execute()

        headers = {h["name"]: h["value"] for h in msg["payload"].get("headers", [])}

        # Extract body
        body = ""
        payload = msg["payload"]
        if "parts" in payload:
            for part in payload["parts"]:
                if part["mimeType"] == "text/plain" and "data" in part.get("body", {}):
                    body = base64.urlsafe_b64decode(part["body"]["data"]).decode("utf-8", errors="replace")
                    break
            if not body:
                for part in payload["parts"]:
                    if part["mimeType"] == "text/html" and "data" in part.get("body", {}):
                        body = base64.urlsafe_b64decode(part["body"]["data"]).decode("utf-8", errors="replace")
                        break
        elif "data" in payload.get("body", {}):
            body = base64.urlsafe_b64decode(payload["body"]["data"]).decode("utf-8", errors="replace")

        # Extract sender email for known contact matching
        from_header = headers.get("From", "")
        from_email = ""
        if "<" in from_header and ">" in from_header:
            from_email = from_header.split("<")[1].split(">")[0].lower()
        else:
            from_email = from_header.lower()

        # Truncate body to avoid huge API calls
        if len(body) > 3000:
            body = body[:3000] + "\n... [truncated]"

        emails.append({
            "message_id": msg["id"],
            "thread_id": msg["threadId"],
            "from": headers.get("From", "Unknown"),
            "from_email": from_email,
            "to": headers.get("To", ""),
            "cc": headers.get("Cc", ""),
            "subject": headers.get("Subject", "No subject"),
            "date": headers.get("Date", ""),
            "snippet": msg.get("snippet", ""),
            "body": body,
            "label_ids": msg.get("labelIds", []),
        })

    return emails


# ─── Main scan loop ──────────────────────────────────────────────────

def run_scan():
    """Execute one full inbox scan cycle."""
    console.print(Panel("🚀 Vessel & Co Gmail Agent — Starting scan", style="bold blue"))
    start_time = datetime.now()

    # Load state
    state = load_state()
    last_scan = state.get("last_scan")
    processed_ids = set(state.get("processed_ids", []))

    # Initialize services
    console.print("  Connecting to Gmail API...")
    service = get_gmail_service(os.getenv("GMAIL_CREDENTIALS_PATH", "credentials.json"))

    console.print("  Connecting to Claude API...")
    claude = anthropic.Anthropic(api_key=os.getenv("ANTHROPIC_API_KEY"))

    # Ensure labels exist
    console.print("  Checking labels...")
    label_names = [cat["gmail_label"] for cat in EMAIL_CATEGORIES.values()]
    label_map = ensure_labels_exist(service, label_names)

    # Fetch new emails
    since_date = None
    if last_scan:
        # Gmail date format: YYYY/MM/DD
        since_dt = datetime.fromisoformat(last_scan) - timedelta(hours=2)  # overlap buffer
        since_date = since_dt.strftime("%Y/%m/%d")

    console.print(f"  Fetching emails{f' since {since_date}' if since_date else ''}...")
    max_emails = int(os.getenv("MAX_EMAILS_PER_SCAN", "50"))
    emails = fetch_new_emails(service, since=since_date, max_results=max_emails)

    # Filter already-processed
    new_emails = [e for e in emails if e["message_id"] not in processed_ids]
    console.print(f"  Found {len(new_emails)} new emails ({len(emails)} total fetched)")

    if not new_emails:
        console.print("[green]  ✓ Inbox is clean — nothing new to process.[/green]")
        state["last_scan"] = datetime.now().isoformat()
        save_state(state)
        return

    # Classify
    console.print(f"  Classifying {len(new_emails)} emails with Claude...")
    classifications = classify_batch(claude, new_emails)

    # Apply labels
    console.print("  Applying labels...")
    for cls in classifications:
        category = cls.get("category", "admin_noise")
        cat_config = EMAIL_CATEGORIES.get(category, {})
        gmail_label = cat_config.get("gmail_label", "Vessel/Admin")
        label_id = label_map.get(gmail_label)
        if label_id:
            try:
                apply_label(service, cls["message_id"], [label_id])
            except Exception as e:
                console.print(f"  [red]Failed to label {cls['subject']}: {e}[/red]")

    # Generate drafts
    console.print("  Generating draft replies...")
    drafts_created = []
    for cls, email in zip(classifications, new_emails):
        if cls.get("needs_reply") and EMAIL_CATEGORIES.get(cls.get("category"), {}).get("auto_draft"):
            try:
                draft_body = generate_draft_reply(claude, email, cls)
                if draft_body:
                    reply_to = email.get("from_email") or email.get("from", "")
                    subject = email.get("subject", "")
                    if not subject.startswith("Re:"):
                        subject = f"Re: {subject}"
                    create_draft(service, reply_to, subject, draft_body, thread_id=email.get("thread_id"))
                    drafts_created.append({
                        "to": reply_to,
                        "subject": subject,
                        "category": cls.get("category"),
                    })
                    console.print(f"    ✓ Draft reply: {subject}")
            except Exception as e:
                console.print(f"    [red]Failed to draft reply for {email.get('subject')}: {e}[/red]")

    # Generate digest
    console.print("  Generating digest...")
    digest_text = generate_digest(classifications, drafts_created)
    digest_path = save_digest(digest_text)
    console.print(f"  ✓ Digest saved: {digest_path}")

    # Send notifications
    console.print("  Sending notifications...")
    urgent_count = len([c for c in classifications if c.get("priority") == "urgent" or c.get("escalation_flags")])
    try:
        send_urgent_alert(classifications)
        send_scan_summary(len(new_emails), urgent_count, len(drafts_created))
    except Exception as e:
        console.print(f"  [yellow]SMS notification failed (Twilio may not be configured): {e}[/yellow]")
    try:
        send_digest_email(service, digest_text)
    except Exception as e:
        console.print(f"  [yellow]Digest email failed: {e}[/yellow]")

    # Print summary table
    table = Table(title="Scan Results", show_lines=True)
    table.add_column("Priority", style="bold", width=10)
    table.add_column("Category", width=20)
    table.add_column("From", width=25)
    table.add_column("Subject", width=40)
    table.add_column("Draft?", width=6)

    priority_styles = {"urgent": "red bold", "high": "yellow", "medium": "cyan", "low": "dim", "ignore": "dim"}
    for cls in sorted(classifications, key=lambda c: ["urgent", "high", "medium", "low", "ignore"].index(c.get("priority", "low"))):
        style = priority_styles.get(cls.get("priority", "low"), "")
        drafted = "✓" if any(d["subject"].endswith(cls.get("subject", "")) for d in drafts_created) else ""
        table.add_row(
            cls.get("priority", "low").upper(),
            cls.get("category", "unknown"),
            cls.get("from", "Unknown")[:25],
            cls.get("subject", "No subject")[:40],
            drafted,
            style=style,
        )
    console.print(table)

    # Update state
    state["last_scan"] = datetime.now().isoformat()
    state["processed_ids"] = list(processed_ids | {e["message_id"] for e in new_emails})
    # Keep only last 500 IDs to prevent state bloat
    if len(state["processed_ids"]) > 500:
        state["processed_ids"] = state["processed_ids"][-500:]
    save_state(state)

    elapsed = (datetime.now() - start_time).seconds
    console.print(Panel(
        f"✅ Scan complete — {len(new_emails)} emails processed, "
        f"{len(drafts_created)} drafts created, {elapsed}s elapsed",
        style="bold green",
    ))


def run_scheduled():
    """Run agent on a schedule."""
    interval = int(os.getenv("SCAN_INTERVAL_MINUTES", "60"))
    console.print(f"[bold]Starting scheduled mode — scanning every {interval} minutes[/bold]")
    console.print("Press Ctrl+C to stop.\n")

    # Run immediately on start
    run_scan()

    schedule.every(interval).minutes.do(run_scan)

    try:
        while True:
            schedule.run_pending()
            time.sleep(30)
    except KeyboardInterrupt:
        console.print("\n[yellow]Agent stopped.[/yellow]")


# ─── CLI ──────────────────────────────────────────────────────────────

if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Vessel & Co Gmail Agent")
    parser.add_argument("--schedule", action="store_true", help="Run on hourly schedule")
    parser.add_argument("--digest", action="store_true", help="Generate digest from last scan only")
    args = parser.parse_args()

    if args.schedule:
        run_scheduled()
    elif args.digest:
        console.print("[yellow]Digest-only mode not yet implemented — run full scan instead.[/yellow]")
    else:
        run_scan()
