
import sqlite3
import os
from datetime import datetime, timedelta, timezone
import random

DB_PATH = os.path.join(os.path.dirname(__file__), "support_crm.db")


def seed_database():
    conn = sqlite3.connect(DB_PATH)
    conn.execute("PRAGMA foreign_keys = ON")

    def ts(days_ago):
        dt = datetime.now(timezone.utc) - timedelta(days=days_ago)
        return dt.strftime("%Y-%m-%dT%H:%M:%SZ")

    TICKETS = [
        {
            "customer_name": "Priya Sharma",
            "customer_email": "priya.sharma@techcorp.in",
            "subject": "Payment gateway timeout on checkout",
            "description": "Users are experiencing timeout errors when attempting to complete payments.",
            "priority": "Urgent",
            "status": "Open",
        },
        {
            "customer_name": "James Okafor",
            "customer_email": "james.okafor@globalretail.com",
            "subject": "Bulk CSV import producing duplicate entries",
            "description": "CSV imports are creating duplicate SKUs after the v2.3 update.",
            "priority": "High",
            "status": "In Progress",
        },
        {
            "customer_name": "Sophie Chen",
            "customer_email": "schen@designstudio.io",
            "subject": "Mobile app crashes on iOS 17.4",
            "description": "Analytics dashboard crashes on iPhone 15 Pro.",
            "priority": "High",
            "status": "Open",
        },
        {
            "customer_name": "Rohan Mehta",
            "customer_email": "rohan.m@startup.co",
            "subject": "API rate limits hitting unexpectedly",
            "description": "Receiving rate limits lower than plan specifications.",
            "priority": "Urgent",
            "status": "Open",
        },
        {
            "customer_name": "Maria Santos",
            "customer_email": "maria.santos@enterprise.br",
            "subject": "SSO integration failing with Okta",
            "description": "Users receive SAML assertion errors.",
            "priority": "High",
            "status": "In Progress",
        },
        {
            "customer_name": "Kenji Tanaka",
            "customer_email": "k.tanaka@jplogistics.jp",
            "subject": "Email notifications not delivered",
            "description": "Corporate emails are not receiving notifications.",
            "priority": "Medium",
            "status": "Open",
        },
        {
            "customer_name": "Emma Williams",
            "customer_email": "emma.w@healthtech.org",
            "subject": "Data export missing custom fields",
            "description": "CSV exports exclude custom fields.",
            "priority": "Medium",
            "status": "Closed",
        },
        {
            "customer_name": "Ahmed Hassan",
            "customer_email": "a.hassan@fintech.ae",
            "subject": "2FA SMS not delivered",
            "description": "Users are not receiving verification codes.",
            "priority": "High",
            "status": "Open",
        },
        {
            "customer_name": "Lucia Fernandez",
            "customer_email": "lucia.f@mediagroup.es",
            "subject": "Video upload stuck at 99%",
            "description": "Large files never complete processing.",
            "priority": "Medium",
            "status": "In Progress",
        },
        {
            "customer_name": "David Park",
            "customer_email": "dpark@consulting.kr",
            "subject": "Dashboard charts blank in Firefox",
            "description": "Charts render as empty boxes.",
            "priority": "Low",
            "status": "Closed",
        },
    ]

    NOTES = {
        "In Progress": [
            (
                "Ticket reviewed and assigned to engineering.",
                "Support Agent",
                2,
            ),
            (
                "Issue reproduced and fix is in progress.",
                "Senior Engineer",
                1,
            ),
        ],
        "Closed": [
            (
                "Patch deployed successfully.",
                "Support Agent",
                3,
            ),
            (
                "Customer confirmed resolution.",
                "Support Agent",
                1,
            ),
        ],
    }

    count = conn.execute(
        "SELECT COUNT(*) FROM tickets"
    ).fetchone()[0]

    if count == 0:
        for i, t in enumerate(TICKETS, start=1):
            ticket_id = f"TKT-{str(i).zfill(4)}"
            created = ts(random.randint(4, 14))
            updated = ts(random.randint(0, 3))

            conn.execute(
                """
                INSERT INTO tickets
                (ticket_id, customer_name, customer_email,
                 subject, description, priority,
                 status, created_at, updated_at)
                VALUES (?,?,?,?,?,?,?,?,?)
                """,
                (
                    ticket_id,
                    t["customer_name"],
                    t["customer_email"],
                    t["subject"],
                    t["description"],
                    t["priority"],
                    t["status"],
                    created,
                    updated,
                ),
            )

            for note_text, author, age in NOTES.get(t["status"], []):
                conn.execute(
                    """
                    INSERT INTO notes
                    (ticket_id, note_text, author, created_at)
                    VALUES (?,?,?,?)
                    """,
                    (
                        ticket_id,
                        note_text,
                        author,
                        ts(age),
                    ),
                )

    conn.commit()
    conn.close()

    print("✅ Sample tickets seeded")

