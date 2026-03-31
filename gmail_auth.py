"""
Gmail API Authentication — OAuth2 flow for Vessel & Co Gmail Agent.

Local dev: opens browser for Google OAuth consent, saves token.json.
Railway/cloud: reads GMAIL_TOKEN_JSON env var (no browser needed).

Setup for Railway:
  1. Run `python generate_token.py` locally to do the OAuth flow
  2. Copy the output JSON string
  3. Set GMAIL_TOKEN_JSON env var in Railway with that value
"""

import os
import json
import base64
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


def _write_credentials_from_env():
    """If GMAIL_CREDENTIALS_JSON env var is set, write it to disk so
    the OAuth flow can use it. Returns the path or None."""
    creds_json = os.getenv("GMAIL_CREDENTIALS_JSON")
    if creds_json:
        path = "/tmp/credentials.json"
        with open(path, "w") as f:
            f.write(creds_json)
        return path
    return None


def get_gmail_service(credentials_path: str = "credentials.json"):
    """Authenticate and return a Gmail API service instance.

    Auth priority:
      1. Existing token.json file on disk
      2. GMAIL_TOKEN_JSON env var (for Railway/cloud)
      3. Interactive OAuth flow using credentials.json (local dev only)
    """
    creds = None

    # --- Try loading token from disk ---
    if os.path.exists(TOKEN_PATH):
        creds = Credentials.from_authorized_user_file(TOKEN_PATH, SCOPES)

    # --- Try loading token from env var ---
    if not creds:
        token_json = os.getenv("GMAIL_TOKEN_JSON")
        if token_json:
            token_data = json.loads(token_json)
            creds = Credentials.from_authorized_user_info(token_data, SCOPES)
            # Write to disk so refresh can persist within this deploy
            with open(TOKEN_PATH, "w") as f:
                f.write(creds.to_json())

    # --- Refresh expired token ---
    if creds and creds.expired and creds.refresh_token:
        try:
            creds.refresh(Request())
            # Save refreshed token to disk
            with open(TOKEN_PATH, "w") as f:
                f.write(creds.to_json())
        except Exception as e:
            print(f"  [WARN] Token refresh failed: {e}")
            creds = None

    # --- If still no valid creds, try interactive OAuth (local only) ---
    if not creds or not creds.valid:
        # Check for credentials file from env var
        env_creds_path = _write_credentials_from_env()
        creds_path = env_creds_path or credentials_path

        if not os.path.exists(creds_path):
            raise FileNotFoundError(
                f"No valid authentication found. Options:\n"
                f"  1. Set GMAIL_TOKEN_JSON env var (for Railway — run generate_token.py locally first)\n"
                f"  2. Place {credentials_path} in project root (for local dev)\n\n"
                f"To generate a token for Railway:\n"
                f"  python generate_token.py\n"
            )

        flow = InstalledAppFlow.from_client_secrets_file(creds_path, SCOPES)
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
