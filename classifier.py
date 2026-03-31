"""
Email Classifier — Uses Claude API to categorize and prioritize emails.
"""

import json
import anthropic
from config import EMAIL_CATEGORIES, ESCALATION_RULES, KNOWN_CONTACTS


def build_classification_prompt():
    """Build the system prompt for email classification."""
    categories_desc = "\n".join(
        f'- "{key}": {cat["description"]}'
        for key, cat in EMAIL_CATEGORIES.items()
    )

    escalation_desc = "\n".join(
        f'- {rule["flag"]}: {rule["description"]}'
        for rule in ESCALATION_RULES
    )

    known_contacts_desc = "\n".join(
        f'- {email}: {info.get("name", "Unknown")} ({info.get("role", "unknown")})'
        for email, info in KNOWN_CONTACTS.items()
    )

    return f"""You are an email classifier for Vessel & Co, a yacht management company.

CATEGORIES (pick exactly one):
{categories_desc}

ESCALATION FLAGS (add if applicable — can be multiple or none):
{escalation_desc}

KNOWN CONTACTS:
{known_contacts_desc}

For each email, return a JSON object with:
{{
    "category": "<category_key>",
    "escalation_flags": ["FLAG1", "FLAG2"] or [],
    "priority": "urgent" | "high" | "medium" | "low" | "ignore",
    "summary": "<1-2 sentence summary of what this email is about and what action is needed>",
    "needs_reply": true/false,
    "reply_context": "<if needs_reply is true, brief context for what the reply should address>"
}}

RULES:
- If the sender is a known contact, use that context for better classification
- If escalation rules match, bump priority to "urgent" regardless of category default
- "needs_reply" should be true if the email asks a question, requests info, or expects a response
- "needs_reply" should be false for notifications, confirmations, FYI-only emails, and automated system emails
- Be precise with summaries — include names, amounts, dates when present
"""


def classify_email(client: anthropic.Anthropic, email_data: dict) -> dict:
    """Classify a single email using Claude."""
    system_prompt = build_classification_prompt()

    email_text = f"""FROM: {email_data.get('from', 'Unknown')}
TO: {email_data.get('to', 'Unknown')}
CC: {email_data.get('cc', '')}
SUBJECT: {email_data.get('subject', 'No subject')}
DATE: {email_data.get('date', 'Unknown')}

BODY:
{email_data.get('body', email_data.get('snippet', 'No content'))}
"""

    response = client.messages.create(
        model="claude-sonnet-4-5-20250514",
        max_tokens=500,
        system=system_prompt,
        messages=[
            {
                "role": "user",
                "content": f"Classify this email:\n\n{email_text}",
            }
        ],
    )

    # Parse JSON from response
    response_text = response.content[0].text.strip()
    # Handle markdown code blocks
    if response_text.startswith("```"):
        response_text = response_text.split("\n", 1)[1].rsplit("```", 1)[0].strip()

    try:
        return json.loads(response_text)
    except json.JSONDecodeError:
        return {
            "category": "admin_noise",
            "escalation_flags": [],
            "priority": "low",
            "summary": f"Could not classify: {email_data.get('subject', 'Unknown')}",
            "needs_reply": False,
            "reply_context": "",
        }


def classify_batch(client: anthropic.Anthropic, emails: list[dict]) -> list[dict]:
    """Classify a batch of emails. Returns list of classification results."""
    results = []
    for email in emails:
        result = classify_email(client, email)
        result["message_id"] = email.get("message_id")
        result["thread_id"] = email.get("thread_id")
        result["from"] = email.get("from", "Unknown")
        result["subject"] = email.get("subject", "No subject")
        result["date"] = email.get("date", "Unknown")
        results.append(result)
    return results
