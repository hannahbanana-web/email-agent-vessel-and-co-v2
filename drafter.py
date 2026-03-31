"""
Auto-Draft Reply Engine — Generates context-aware draft replies using Claude.
"""

import anthropic
from config import DRAFT_SYSTEM_PROMPT, KNOWN_CONTACTS, EMAIL_CATEGORIES


def generate_draft_reply(
    client: anthropic.Anthropic,
    email_data: dict,
    classification: dict,
) -> str | None:
    """Generate a draft reply for an email that needs a response.

    Returns the draft body text, or None if no draft should be created.
    """
    category = classification.get("category", "")
    cat_config = EMAIL_CATEGORIES.get(category, {})

    # Skip if category doesn't have auto_draft enabled
    if not cat_config.get("auto_draft", False):
        return None

    # Skip if classifier says no reply needed
    if not classification.get("needs_reply", False):
        return None

    # Build context about the sender
    sender_email = email_data.get("from_email", "")
    sender_info = KNOWN_CONTACTS.get(sender_email, {})
    sender_context = ""
    if sender_info:
        sender_context = f"""
KNOWN SENDER INFO:
- Name: {sender_info.get('name', 'Unknown')}
- Role: {sender_info.get('role', 'Unknown')}
- Company: {sender_info.get('company', sender_info.get('note', 'N/A'))}
- Vessel: {sender_info.get('vessel', 'N/A')}
"""

    user_prompt = f"""Draft a reply to this email.

CLASSIFICATION: {classification.get('category')} | Priority: {classification.get('priority')}
REPLY CONTEXT: {classification.get('reply_context', 'General response needed')}
{sender_context}
--- ORIGINAL EMAIL ---
FROM: {email_data.get('from', 'Unknown')}
SUBJECT: {email_data.get('subject', '')}
DATE: {email_data.get('date', '')}

{email_data.get('body', email_data.get('snippet', ''))}
--- END ---

Write ONLY the reply body (no subject line, no headers). Keep it concise and professional.
If you don't have enough information to give a complete answer (rates, availability, etc.), acknowledge the inquiry warmly and say you'll confirm the details and follow up shortly.
"""

    response = client.messages.create(
        model="claude-sonnet-4-6",
        max_tokens=800,
        system=DRAFT_SYSTEM_PROMPT,
        messages=[{"role": "user", "content": user_prompt}],
    )

    return response.content[0].text.strip()
