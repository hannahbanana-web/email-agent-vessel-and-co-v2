# Vessel & Co Gmail Agent

Autonomous Python agent that manages the hello@vesselandco.yachts inbox — classifies emails, applies labels, drafts replies, and generates digests.

## What it does

Every hour (or on demand), the agent:

1. **Fetches** new inbox emails since the last scan
2. **Classifies** each email into categories (charter inquiry, booking, contract, payment, etc.) using Claude
3. **Applies Gmail labels** automatically (creates them if they don't exist)
4. **Drafts replies** for actionable emails — charter inquiries, payment follow-ups, industry intros, crew, and owner comms
5. **Generates a digest** summarizing what came in, what's urgent, and what drafts are queued

All drafts are saved for your review — nothing sends automatically.

## Setup (10 minutes)

### 1. Google Cloud Console — Gmail API credentials

1. Go to [Google Cloud Console](https://console.cloud.google.com/)
2. Create a new project (or use existing)
3. Enable the **Gmail API**: APIs & Services → Library → search "Gmail API" → Enable
4. Create credentials: APIs & Services → Credentials → Create Credentials → OAuth 2.0 Client ID
5. Application type: **Desktop app**
6. Download the JSON file → save as `credentials.json` in this folder

### 2. Anthropic API key

1. Go to [Anthropic Console](https://console.anthropic.com/)
2. Create an API key
3. Copy it

### 3. Configure

```bash
cp .env.example .env
```

Edit `.env` and add your Anthropic API key.

### 4. Install dependencies

```bash
pip install -r requirements.txt
```

### 5. First run (authenticates Gmail)

```bash
python agent.py
```

This opens a browser window for Google OAuth consent. Sign in with hello@vesselandco.yachts and grant access. A `token.json` file is saved for future runs.

### 6. Run on schedule

```bash
python agent.py --schedule
```

This runs the scan immediately, then every 60 minutes. Adjust `SCAN_INTERVAL_MINUTES` in `.env`.

## File structure

```
vessel-gmail-agent/
├── agent.py          # Main runner — CLI entry point
├── gmail_auth.py     # Gmail OAuth2 + label/draft helpers
├── classifier.py     # Claude-powered email classifier
├── drafter.py        # Auto-draft reply generator
├── digest.py         # Digest report generator
├── config.py         # Categories, contacts, prompts, rules
├── requirements.txt  # Python dependencies
├── .env.example      # Environment template
├── credentials.json  # (you add this — Google OAuth)
├── token.json        # (auto-generated after first auth)
└── agent_state.json  # (auto-generated — tracks processed emails)
```

## Gmail labels created

The agent creates these labels automatically:

- `Vessel/Charter-Inquiry`
- `Vessel/Booking`
- `Vessel/Contract`
- `Vessel/Payment`
- `Vessel/Industry`
- `Vessel/Operations`
- `Vessel/Crew`
- `Vessel/Owner`
- `Vessel/Vendor`
- `Vessel/Marketing`
- `Vessel/Admin`

## Customizing

**Add contacts**: Edit `KNOWN_CONTACTS` in `config.py` — the classifier uses these for smarter categorization.

**Adjust draft tone**: Edit `DRAFT_SYSTEM_PROMPT` in `config.py`.

**Change categories**: Edit `EMAIL_CATEGORIES` in `config.py`. Each category has a description (used by Claude for classification), priority level, and auto_draft flag.

**Escalation rules**: Edit `ESCALATION_RULES` in `config.py` to change what gets flagged as urgent.

## Running as a background service

For always-on operation, use a process manager:

```bash
# With nohup
nohup python agent.py --schedule > agent.log 2>&1 &

# With systemd (create /etc/systemd/system/vessel-gmail-agent.service)
# With pm2 (if you have Node.js)
pm2 start agent.py --interpreter python3 --name vessel-gmail
```

## Cost estimate

Each scan classifies emails using Claude Sonnet + generates drafts. Rough estimate:
- 20 emails/scan × 2 API calls avg = ~40 API calls/scan
- ~$0.05-0.15 per scan depending on email length
- Hourly: ~$1-3/day
