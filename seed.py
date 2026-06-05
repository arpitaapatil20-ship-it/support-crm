"""
seed.py — Populate support_crm.db with sample tickets and notes.
Run once after cloning:  python seed.py
"""

import sqlite3
import os
from datetime import datetime, timedelta, timezone
import random

DB_PATH = os.path.join(os.path.dirname(__file__), "support_crm.db")

# ── Schema ────────────────────────────────────────────
conn = sqlite3.connect(DB_PATH)
conn.execute("PRAGMA foreign_keys = ON")

conn.executescript("""
    CREATE TABLE IF NOT EXISTS tickets (
        id             INTEGER PRIMARY KEY AUTOINCREMENT,
        ticket_id      TEXT    UNIQUE NOT NULL,
        customer_name  TEXT    NOT NULL,
        customer_email TEXT    NOT NULL,
        subject        TEXT    NOT NULL,
        description    TEXT    NOT NULL,
        priority       TEXT    NOT NULL DEFAULT 'Medium',
        status         TEXT    NOT NULL DEFAULT 'Open',
        created_at     TEXT    NOT NULL,
        updated_at     TEXT    NOT NULL
    );
    CREATE TABLE IF NOT EXISTS notes (
        id         INTEGER PRIMARY KEY AUTOINCREMENT,
        ticket_id  TEXT    NOT NULL REFERENCES tickets(ticket_id) ON DELETE CASCADE,
        note_text  TEXT    NOT NULL,
        author     TEXT    NOT NULL DEFAULT 'Support Agent',
        created_at TEXT    NOT NULL
    );
""")

# Clear existing data
conn.execute("DELETE FROM notes")
conn.execute("DELETE FROM tickets")
conn.commit()

# ── Sample data ───────────────────────────────────────
def ts(days_ago):
    dt = datetime.now(timezone.utc) - timedelta(days=days_ago)
    return dt.strftime("%Y-%m-%dT%H:%M:%SZ")

TICKETS = [
    {
        "customer_name":  "Priya Sharma",
        "customer_email": "priya.sharma@techcorp.in",
        "subject":        "Payment gateway timeout on checkout",
        "description":    "Users are experiencing timeout errors when attempting to complete payments. Roughly 1 in 5 transactions fail with a 504 error. Our payment provider says the problem is on our end. This is causing significant revenue loss.",
        "priority": "Urgent", "status": "Open",
    },
    {
        "customer_name":  "James Okafor",
        "customer_email": "james.okafor@globalretail.com",
        "subject":        "Bulk CSV import producing duplicate entries",
        "description":    "When importing our product catalog via the CSV bulk import tool, approximately 15% of SKUs are being duplicated. The issue started after the v2.3 update. We have 50,000+ products affected and inventory counts are now wrong.",
        "priority": "High", "status": "In Progress",
    },
    {
        "customer_name":  "Sophie Chen",
        "customer_email": "schen@designstudio.io",
        "subject":        "Mobile app crashes on iOS 17.4",
        "description":    "The mobile app consistently crashes when navigating to the analytics dashboard on devices running iOS 17.4. Older iOS versions seem unaffected. Reproducible 100% of the time on iPhone 15 Pro. Crash log attached separately.",
        "priority": "High", "status": "Open",
    },
    {
        "customer_name":  "Rohan Mehta",
        "customer_email": "rohan.m@startup.co",
        "subject":        "API rate limits hitting unexpectedly",
        "description":    "We are being rate-limited at 200 requests/minute but our subscription plan states 1000 req/min. This is severely impacting our production environment and causing cascade failures. Started approximately 3 days ago with no config changes on our side.",
        "priority": "Urgent", "status": "Open",
    },
    {
        "customer_name":  "Maria Santos",
        "customer_email": "maria.santos@enterprise.br",
        "subject":        "SSO integration failing with Okta",
        "description":    "After upgrading to the Enterprise plan, SSO with Okta stopped working. Users receive 'SAML assertion invalid' errors. The setup worked perfectly on the previous plan. Downgrading is not an option as we are mid-rollout to 800 employees.",
        "priority": "High", "status": "In Progress",
    },
    {
        "customer_name":  "Kenji Tanaka",
        "customer_email": "k.tanaka@jplogistics.jp",
        "subject":        "Email notifications not delivered to custom domain",
        "description":    "Transactional emails (order confirmations, password resets) are not being delivered to corporate addresses @jplogistics.jp. Gmail addresses work fine. SPF, DKIM, and DMARC records are correctly configured and verified.",
        "priority": "Medium", "status": "Open",
    },
    {
        "customer_name":  "Emma Williams",
        "customer_email": "emma.w@healthtech.org",
        "subject":        "Data export missing custom fields",
        "description":    "When exporting patient records to CSV, all custom fields added in the last 6 months are absent. Standard fields export correctly. This is blocking our quarterly compliance reporting submission due next Friday.",
        "priority": "Medium", "status": "Closed",
    },
    {
        "customer_name":  "Ahmed Hassan",
        "customer_email": "a.hassan@fintech.ae",
        "subject":        "Two-factor authentication SMS not delivered",
        "description":    "2FA SMS codes are not being received by users in the UAE and Saudi Arabia. The issue affects both new and existing users. Authentication apps work as a workaround but most of our users do not have them configured.",
        "priority": "High", "status": "Open",
    },
    {
        "customer_name":  "Lucia Fernandez",
        "customer_email": "lucia.f@mediagroup.es",
        "subject":        "Video upload processing stuck at 99%",
        "description":    "Large video files (>2 GB) get stuck at 99% during processing and never complete. The issue started after last week's infrastructure update. Smaller files upload fine. We currently have 47 videos queued and a broadcast deadline tomorrow.",
        "priority": "Medium", "status": "In Progress",
    },
    {
        "customer_name":  "David Park",
        "customer_email": "dpark@consulting.kr",
        "subject":        "Dashboard charts blank in Firefox 124+",
        "description":    "The analytics dashboard charts render as blank white boxes in Firefox 124 and above. Chrome and Safari display correctly. The browser console shows 'WebGL context lost' errors. Affects roughly 30% of our user base.",
        "priority": "Low", "status": "Closed",
    },
]

NOTES = {
    "In Progress": [
        ("Ticket reviewed and assigned to the engineering team. Initial investigation is underway.", "Support Agent", 2),
        ("Reproduced the issue in our staging environment. A fix is being developed and will be in the next patch.", "Senior Engineer", 1),
    ],
    "Closed": [
        ("Root cause identified. A patch has been deployed to production. Please confirm whether the issue is resolved on your end.", "Support Agent", 3),
        ("Customer confirmed the issue is resolved. Closing ticket.", "Support Agent", 1),
    ],
}

for i, t in enumerate(TICKETS, start=1):
    ticket_id = f"TKT-{str(i).zfill(4)}"
    created   = ts(random.randint(4, 14))
    updated   = ts(random.randint(0, 3))
    conn.execute(
        "INSERT INTO tickets (ticket_id, customer_name, customer_email, subject, description, priority, status, created_at, updated_at) VALUES (?,?,?,?,?,?,?,?,?)",
        (ticket_id, t["customer_name"], t["customer_email"], t["subject"], t["description"], t["priority"], t["status"], created, updated),
    )
    for note_text, author, age in NOTES.get(t["status"], []):
        conn.execute(
            "INSERT INTO notes (ticket_id, note_text, author, created_at) VALUES (?,?,?,?)",
            (ticket_id, note_text, author, ts(age)),
        )

conn.commit()
conn.close()
print(f"✅  Seeded {len(TICKETS)} tickets into {DB_PATH}")
