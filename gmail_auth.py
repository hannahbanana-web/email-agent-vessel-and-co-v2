"""
Gmail API Authentication — OAuth2 flow for Vessel & Co Gmail Agent.

First run: opens browser for Google OAuth consent.
Subsequent runs: uses cached token.json.
"""

import os
from google.auth.transport.requests import Request
from google.oauth2.credentials import Credentials
from google_auth_oauthlib.flow import InstalledAppFlow
from googleapiclient.discovery import build

# Full Gmail access — needed for labels, drafts, and reading
SCOPES = [
    "https://www.googleapis.com/auth/gmail.modify",
    "https://www.googleapis.com/auth/gmail.compose",
    "https://www.googleapis.com/auth/gmail.labels",
]

TOKEN_PATH = "token.json"


def get_gmail_service(credentials_path: str = "credentials.json"):
    """Authenticate and return a Gmail API service instance."""
    creds = None

    if os.path.exists(TOKEN_PATH):
        creds = Credentials.from_authorized_user_file(TOKEN_PATH, SCOPES)

    if not creds or not creds.valid:
        if creds and creds.expired and creds.refresh_token:
            creds.refresh(Request())
        else:
            # Check if we have token data in env (for Railway/cloud deployment)
            token_json = os.getenv("GMAIL_TOKEN_JSON")
            if token_json:
                import json
                token_data = json.loads(token_json)
                creds = Credentials.from_authorized_user_info(token_data, SCOPES)
            elif not os.path.exists(credentials_path):
                raise FileNotFoundError(
                    f"Missing {credentials_path}. Download it from Google Cloud Console:\n"
                    "https://console.cloud.google.com/apis/credentials\n"
                    "Create an OAuth 2.0 Client ID (Desktop app), download JSON, save as credentials.json"
                )
            else:
                flow = InstalledAppFlow.from_client_secrets_file(credentials_path, SCOPES)
                creds = flow.run_local_server(port=0)

        with open(TOKEN_PATH, "w") as token:
            token.write(creds.to_json())

    return build("gmail", "v1", credentials=creds)


def ensure_labels_exist(service, labels_to_create: list[str]):
    """Create Gmail labels if they don't already exist. Returns {label_name: label_id} map."""
    existing = service.users().labels().list(userId="me").execute()
    existing_names = {l["name"]: l["id"] for l in existing.get("labels", [])}

    label_map = {}
    for label_name in labels_to_create:
        if label_name in existing_names:
            label_map[label_name] = existing_names[label_name]
        else:
            body = {
                "name": label_name,
                "labelListVisibility": "labelShow",
                "messageListVisibility": "show",
            }
            result = service.users().labels().create(userId="me", body=body).execute()
            label_map[label_name] = result["id"]
            print(f"  ✓ Created label: {label_name}")

    return label_map


def apply_label(service, message_id: str, label_ids: list[str], remove_label_ids: list[str] = None):
    """Apply labels to a message (and optionally remove others)."""
    body = {"addLabelIds": label_ids}
    if remove_label_ids:
        body["removeLabelIds"] = remove_label_ids
    service.users().messages().modify(userId="me", id=message_id, body=body).execute()


def create_draft(service, to: str, subject: str, body: str, thread_id: str = None):
    """Create a Gmail draft. If thread_id provided, it's a reply."""
    import base64
    from email.mime.text import MIMEText

    message = MIMEText(body)
    message["to"] = to
    message["subject"] = subject

    raw = base64.urlsafe_b64encode(message.as_bytes()).decode()
    draft_body = {"message": {"raw": raw}}
    if thread_id:
        draft_body["message"]["threadId"] = thread_id

    return service.users().drafts().create(userId="me", body=draft_body).execute()
