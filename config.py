"""
Vessel & Co Gmail Agent — Configuration
Email categories, priority rules, and draft templates for PurelyBlu / Vessel & Co operations.
"""

# ─── Email Categories ───────────────────────────────────────────────
# Each category has: name, description (for Claude classifier), priority level, auto_draft flag

EMAIL_CATEGORIES = {
    "charter_inquiry": {
        "label": "Charter Inquiry",
        "description": "Broker or client asking about yacht availability, rates, itineraries, or booking PurelyBlu or any managed vessel. Includes initial inquiries, follow-ups on availability, guest count questions.",
        "priority": "high",
        "auto_draft": True,
        "gmail_label": "Vessel/Charter-Inquiry",
    },
    "booking_confirmed": {
        "label": "Booking Confirmed",
        "description": "Charter booking confirmations, working holds, option taken notices, or confirmed reservations. Includes Central Yacht Agent notifications about holds.",
        "priority": "high",
        "auto_draft": False,
        "gmail_label": "Vessel/Booking",
    },
    "contract": {
        "label": "Contract & DocuSign",
        "description": "Charter contracts, management agreements, DocuSign envelopes (sent, completed, voided), contract negotiations, or any legally binding documents.",
        "priority": "high",
        "auto_draft": False,
        "gmail_label": "Vessel/Contract",
    },
    "payment_financial": {
        "label": "Payment & Financial",
        "description": "Escrow payments, wire transfers, commission discussions, banking details requests, payment confirmations, Mercury bank notifications, Stripe notifications.",
        "priority": "high",
        "auto_draft": True,
        "gmail_label": "Vessel/Payment",
    },
    "industry_partnership": {
        "label": "Industry & Partnership",
        "description": "Industry organizations (CYBA, MYBA), awards, press/media (Boat International, Dockwalk), partnership opportunities, advertising inquiries, networking intros.",
        "priority": "medium",
        "auto_draft": True,
        "gmail_label": "Vessel/Industry",
    },
    "vessel_operations": {
        "label": "Vessel Operations",
        "description": "Vessel maintenance, refit, build updates (Luna, PurelyBlu), crew matters, provisioning, equipment, surveys, flag state, compliance, insurance.",
        "priority": "medium",
        "auto_draft": False,
        "gmail_label": "Vessel/Operations",
    },
    "crew": {
        "label": "Crew",
        "description": "Crew hiring, applications, crew placement, day workers, crew references, crew scheduling.",
        "priority": "medium",
        "auto_draft": True,
        "gmail_label": "Vessel/Crew",
    },
    "client_owner": {
        "label": "Client / Owner",
        "description": "Communications with yacht owners, owner updates, owner reporting, management updates for vessel owners.",
        "priority": "high",
        "auto_draft": True,
        "gmail_label": "Vessel/Owner",
    },
    "vendor_service": {
        "label": "Vendor & Service Provider",
        "description": "Marina, dockage, fuel, provisioning vendors, yacht services, cleaning, repairs, surveyor, marine electronics, canvas, etc.",
        "priority": "low",
        "auto_draft": False,
        "gmail_label": "Vessel/Vendor",
    },
    "marketing_brand": {
        "label": "Marketing & Brand",
        "description": "Mailchimp, social media platforms, website/GoDaddy, SEO, brand mentions, marketing campaigns, newsletter.",
        "priority": "low",
        "auto_draft": False,
        "gmail_label": "Vessel/Marketing",
    },
    "admin_noise": {
        "label": "Admin / Noise",
        "description": "Verification codes, password resets, Google notifications, subscription renewals, forwarding confirmations, automated system emails with no action needed.",
        "priority": "ignore",
        "auto_draft": False,
        "gmail_label": "Vessel/Admin",
    },
}

# ─── Priority Escalation Rules ──────────────────────────────────────
# Emails matching these get bumped to URGENT regardless of category

ESCALATION_RULES = [
    {
        "name": "money_in_motion",
        "description": "Any email about wire transfers sent, payment due, escrow deadlines, or overdue payments",
        "flag": "URGENT_FINANCIAL",
    },
    {
        "name": "time_sensitive_booking",
        "description": "Working holds, options expiring, booking deadlines within 48 hours, or broker saying client is ready to book NOW",
        "flag": "URGENT_BOOKING",
    },
    {
        "name": "contract_deadline",
        "description": "Contracts awaiting signature, DocuSign pending action, counter-offers with deadlines",
        "flag": "URGENT_CONTRACT",
    },
    {
        "name": "owner_direct",
        "description": "Direct email from a yacht owner (Greg McKelvey, Tom Kennedy, etc.)",
        "flag": "OWNER_DIRECT",
    },
]

# ─── Known Contacts ─────────────────────────────────────────────────
# Key contacts for smarter classification and draft personalization

KNOWN_CONTACTS = {
    "greg@purelyblu.com": {"name": "Greg McKelvey", "role": "owner", "vessel": "PurelyBlu"},
    "tomkennedy@c4.net": {"name": "Tom Kennedy", "role": "owner", "vessel": "Luna"},
    "trishkennedy@capeview.com": {"name": "Trish Kennedy", "role": "owner", "vessel": "Luna"},
    "kerry@epicyachtcharters.com": {"name": "Kerry Hucul", "role": "broker", "company": "Epic Yacht Charters"},
    "kat@globalyachtgetaways.com": {"name": "Katarina Danks", "role": "broker", "company": "Global Yacht Getaways"},
    "ed@yachtchartersunlimited.com": {"name": "Ed", "role": "broker", "company": "Yacht Charters Unlimited"},
    "kristi@chartersmarter.com": {"name": "Kristi Marquart", "role": "broker", "company": "Charter Smarter"},
    "elizabeth@conciergeyachting.com": {"name": "Beth White", "role": "broker", "company": "Concierge Yachting"},
    "louis@yacht.vacations": {"name": "Louis Odendaal", "role": "broker", "company": "Yacht Vacations"},
    "mandy@wlmscharters.com": {"name": "Mandy Walker", "role": "industry", "company": "WLMS Charters / CYBA"},
    "contracts@cyba.net": {"name": "CYBA Contracts", "role": "industry", "company": "CYBA"},
    "bird@sailingdirections.com": {"name": "Bird Newland", "role": "industry", "company": "Sailing Directions"},
    "john@oceanoutcasts.com": {"name": "John Garza", "role": "internal", "note": "Co-founder / Captain"},
    "hannah@oceanoutcasts.com": {"name": "Hannah Patten", "role": "internal", "note": "Co-founder"},
    "noreply@centralyachtagent.com": {"name": "Central Yacht Agent", "role": "system", "note": "Booking platform notifications"},
    "eric.macklin@catamaranguru.com": {"name": "Eric Macklin", "role": "vendor", "company": "Catamaran Guru"},
    "greg@catamaranguru.com": {"name": "Greg Clum", "role": "vendor", "company": "Catamaran Guru"},
}

# ─── Draft Reply Context ────────────────────────────────────────────
# Gives Claude the right tone and info for auto-drafting

DRAFT_SYSTEM_PROMPT = """You are drafting email replies on behalf of Vessel & Co (hello@vesselandco.yachts).

ABOUT VESSEL & CO:
- High-end yacht management and charter clearinghouse
- Owner-side advocates — we represent yacht owners, not brokers
- Currently managing PurelyBlu (catamaran) and Luna (in build/refit)
- John Garza is USCG-licensed Captain and co-founder
- Hannah Patten is co-founder, handles operations and business development
- Website: https://www.vesselandco.yachts/

VOICE & TONE:
- Luxury but approachable — warm, confident, polished
- Professional but not stuffy — we're real people who live on boats
- Responsive and knowledgeable — we know the industry inside and out
- Never salesy — we build trust through expertise and service

RULES:
- Sign emails as "John & Hannah | Vessel & Co" unless context clearly indicates only one person
- For charter inquiries: be enthusiastic but don't over-commit. Confirm details, ask clarifying questions if needed
- For payment threads: be precise and professional. Confirm amounts and timelines
- For industry contacts: be warm and collegial
- NEVER fabricate availability, rates, or dates — if unsure, say you'll confirm and follow up
- NEVER send the draft automatically — always save as draft for human review
- Keep replies concise — yacht industry people are busy
"""

# ─── Digest Settings ─────────────────────────────────────────────────

DIGEST_TEMPLATE = """
# Vessel & Co — Inbox Digest
**{date}** | {total_emails} new emails processed

## 🔴 Urgent / Action Required
{urgent_section}

## 📋 Charter Activity
{charter_section}

## 💰 Financial
{financial_section}

## 🤝 Industry & Partnerships
{industry_section}

## ⚓ Operations
{operations_section}

## 📝 Drafts Queued ({draft_count})
{drafts_section}

## 🔇 Archived / Low Priority
{noise_section}
"""
