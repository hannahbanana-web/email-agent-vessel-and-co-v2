"""
Digest Generator — Compiles email scan results into a summary digest.
"""

from datetime import datetime
from config import DIGEST_TEMPLATE


def generate_digest(classifications: list[dict], drafts_created: list[dict]) -> str:
    """Generate a formatted digest from classified emails."""
    now = datetime.now().strftime("%A, %B %d, %Y at %I:%M %p")

    # Group by section
    urgent = [c for c in classifications if c.get("priority") == "urgent" or c.get("escalation_flags")]
    charter = [c for c in classifications if c.get("category") in ("charter_inquiry", "booking_confirmed")]
    financial = [c for c in classifications if c.get("category") == "payment_financial"]
    industry = [c for c in classifications if c.get("category") in ("industry_partnership", "crew")]
    operations = [c for c in classifications if c.get("category") in ("vessel_operations", "client_owner")]
    noise = [c for c in classifications if c.get("category") in ("admin_noise", "marketing_brand", "vendor_service")]

    def format_section(items):
        if not items:
            return "_Nothing new._\n"
        lines = []
        for item in items:
            flags = ""
            if item.get("escalation_flags"):
                flags = f" **[{', '.join(item['escalation_flags'])}]**"
            lines.append(
                f"- **{item.get('from', 'Unknown')}** — {item.get('subject', 'No subject')}{flags}\n"
                f"  _{item.get('summary', 'No summary')}_"
            )
        return "\n".join(lines) + "\n"

    def format_drafts(drafts):
        if not drafts:
            return "_No drafts created this scan._\n"
        lines = []
        for d in drafts:
            lines.append(f"- Reply to **{d.get('to', 'Unknown')}** re: {d.get('subject', 'No subject')}")
        return "\n".join(lines) + "\n"

    digest = DIGEST_TEMPLATE.format(
        date=now,
        total_emails=len(classifications),
        urgent_section=format_section(urgent),
        charter_section=format_section(charter),
        financial_section=format_section(financial),
        industry_section=format_section(industry),
        operations_section=format_section(operations),
        drafts_section=format_drafts(drafts_created),
        draft_count=len(drafts_created),
        noise_section=format_section(noise),
    )

    return digest


def save_digest(digest_text: str, output_dir: str = "digests"):
    """Save digest to a markdown file."""
    import os
    os.makedirs(output_dir, exist_ok=True)
    filename = datetime.now().strftime("digest_%Y%m%d_%H%M.md")
    filepath = os.path.join(output_dir, filename)
    with open(filepath, "w") as f:
        f.write(digest_text)
    return filepath
