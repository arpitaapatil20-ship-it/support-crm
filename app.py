import sqlite3
import os
import re
from datetime import datetime, timezone
from flask import Flask, request, jsonify, render_template, g
from flask_cors import CORS

app = Flask(__name__)
CORS(app)

DB_PATH = os.path.join(os.path.dirname(__file__), "support_crm.db")

# ─────────────────────────────────────────────
# Database helpers
# ─────────────────────────────────────────────

def get_db():
    if "db" not in g:
        conn = sqlite3.connect(DB_PATH)
        conn.row_factory = sqlite3.Row
        conn.execute("PRAGMA foreign_keys = ON")
        conn.execute("PRAGMA journal_mode = WAL")
        g.db = conn
    return g.db

@app.teardown_appcontext
def close_db(exc=None):
    db = g.pop("db", None)
    if db is not None:
        db.close()

def init_db():
    """Create tables if they don't exist."""
    with sqlite3.connect(DB_PATH) as conn:
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

def now_iso():
    return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")

def generate_ticket_id(conn):
    row = conn.execute("SELECT COUNT(*) AS cnt FROM tickets").fetchone()
    return f"TKT-{str(row['cnt'] + 1).zfill(4)}"

def row_to_dict(row):
    return dict(row) if row else None

# ─────────────────────────────────────────────
# Frontend route
# ─────────────────────────────────────────────

@app.route("/")
def index():
    return render_template("index.html")

# ─────────────────────────────────────────────
# POST /api/tickets  — Create ticket
# ─────────────────────────────────────────────

@app.route("/api/tickets", methods=["POST"])
def create_ticket():
    data = request.get_json(force=True) or {}

    customer_name  = (data.get("customer_name")  or "").strip()
    customer_email = (data.get("customer_email") or "").strip().lower()
    subject        = (data.get("subject")        or "").strip()
    description    = (data.get("description")    or "").strip()
    priority       = data.get("priority", "Medium")

    # Validation
    if not all([customer_name, customer_email, subject, description]):
        return jsonify({"error": "Missing required fields: customer_name, customer_email, subject, description"}), 400

    if not re.match(r"^[^\s@]+@[^\s@]+\.[^\s@]+$", customer_email):
        return jsonify({"error": "Invalid email address"}), 400

    if priority not in ("Low", "Medium", "High", "Urgent"):
        priority = "Medium"

    db = get_db()
    ticket_id = generate_ticket_id(db)
    ts = now_iso()

    db.execute(
        """INSERT INTO tickets
           (ticket_id, customer_name, customer_email, subject, description, priority, status, created_at, updated_at)
           VALUES (?,?,?,?,?,?,'Open',?,?)""",
        (ticket_id, customer_name, customer_email, subject, description, priority, ts, ts),
    )
    db.commit()

    return jsonify({"ticket_id": ticket_id, "created_at": ts}), 201

# ─────────────────────────────────────────────
# GET /api/tickets  — List tickets
# ─────────────────────────────────────────────

@app.route("/api/tickets", methods=["GET"])
def list_tickets():
    status   = request.args.get("status",   "").strip()
    priority = request.args.get("priority", "").strip()
    search   = request.args.get("search",   "").strip()
    sort     = request.args.get("sort",     "created_at")
    order    = request.args.get("order",    "desc")

    VALID_SORTS  = {"created_at", "updated_at", "status", "customer_name", "priority", "ticket_id"}
    VALID_ORDERS = {"asc", "desc"}
    safe_sort  = sort  if sort  in VALID_SORTS  else "created_at"
    safe_order = order if order in VALID_ORDERS else "desc"

    sql    = "SELECT ticket_id, customer_name, customer_email, subject, status, priority, created_at, updated_at FROM tickets WHERE 1=1"
    params = []

    if status and status != "All":
        sql += " AND status = ?"
        params.append(status)

    if priority and priority != "All":
        sql += " AND priority = ?"
        params.append(priority)

    if search:
        sql += " AND (customer_name LIKE ? OR customer_email LIKE ? OR ticket_id LIKE ? OR subject LIKE ? OR description LIKE ?)"
        term = f"%{search}%"
        params.extend([term, term, term, term, term])

    sql += f" ORDER BY {safe_sort} {safe_order}"

    db = get_db()
    tickets = [row_to_dict(r) for r in db.execute(sql, params).fetchall()]

    stats = row_to_dict(db.execute("""
        SELECT
            COUNT(*)                                          AS total,
            SUM(CASE WHEN status='Open'        THEN 1 ELSE 0 END) AS open,
            SUM(CASE WHEN status='In Progress' THEN 1 ELSE 0 END) AS in_progress,
            SUM(CASE WHEN status='Closed'      THEN 1 ELSE 0 END) AS closed,
            SUM(CASE WHEN priority='Urgent'    THEN 1 ELSE 0 END) AS urgent
        FROM tickets
    """).fetchone())

    return jsonify({"tickets": tickets, "stats": stats})

# ─────────────────────────────────────────────
# GET /api/tickets/<ticket_id>  — Single ticket
# ─────────────────────────────────────────────

@app.route("/api/tickets/<ticket_id>", methods=["GET"])
def get_ticket(ticket_id):
    db     = get_db()
    ticket = row_to_dict(db.execute("SELECT * FROM tickets WHERE ticket_id = ?", (ticket_id,)).fetchone())

    if not ticket:
        return jsonify({"error": f"Ticket {ticket_id} not found"}), 404

    ticket["notes"] = [
        row_to_dict(r)
        for r in db.execute(
            "SELECT * FROM notes WHERE ticket_id = ? ORDER BY created_at ASC", (ticket_id,)
        ).fetchall()
    ]
    return jsonify(ticket)

# ─────────────────────────────────────────────
# PUT /api/tickets/<ticket_id>  — Update ticket
# ─────────────────────────────────────────────

@app.route("/api/tickets/<ticket_id>", methods=["PUT"])
def update_ticket(ticket_id):
    db = get_db()

    if not db.execute("SELECT id FROM tickets WHERE ticket_id = ?", (ticket_id,)).fetchone():
        return jsonify({"error": f"Ticket {ticket_id} not found"}), 404

    data     = request.get_json(force=True) or {}
    status   = data.get("status")
    priority = data.get("priority")
    note     = (data.get("note") or "").strip()
    author   = (data.get("author") or "Support Agent").strip()

    ts      = now_iso()
    sets    = []
    params  = []

    if status in ("Open", "In Progress", "Closed"):
        sets.append("status = ?");   params.append(status)
    if priority in ("Low", "Medium", "High", "Urgent"):
        sets.append("priority = ?"); params.append(priority)

    if sets:
        sets.append("updated_at = ?")
        params.append(ts)
        params.append(ticket_id)
        db.execute(f"UPDATE tickets SET {', '.join(sets)} WHERE ticket_id = ?", params)

    if note:
        db.execute(
            "INSERT INTO notes (ticket_id, note_text, author, created_at) VALUES (?,?,?,?)",
            (ticket_id, note, author, ts),
        )

    db.commit()
    return jsonify({"success": True, "updated_at": ts})

# ─────────────────────────────────────────────
# DELETE /api/tickets/<ticket_id>
# ─────────────────────────────────────────────

@app.route("/api/tickets/<ticket_id>", methods=["DELETE"])
def delete_ticket(ticket_id):
    db = get_db()
    if not db.execute("SELECT id FROM tickets WHERE ticket_id = ?", (ticket_id,)).fetchone():
        return jsonify({"error": f"Ticket {ticket_id} not found"}), 404

    db.execute("DELETE FROM tickets WHERE ticket_id = ?", (ticket_id,))
    db.commit()
    return jsonify({"success": True})

# ─────────────────────────────────────────────
# GET /api/stats  — Dashboard numbers
# ─────────────────────────────────────────────

@app.route("/api/stats", methods=["GET"])
def get_stats():
    db = get_db()

    stats = row_to_dict(db.execute("""
        SELECT
            COUNT(*)                                          AS total,
            SUM(CASE WHEN status='Open'        THEN 1 ELSE 0 END) AS open,
            SUM(CASE WHEN status='In Progress' THEN 1 ELSE 0 END) AS in_progress,
            SUM(CASE WHEN status='Closed'      THEN 1 ELSE 0 END) AS closed,
            SUM(CASE WHEN priority='Urgent'    THEN 1 ELSE 0 END) AS urgent,
            SUM(CASE WHEN priority='High'      THEN 1 ELSE 0 END) AS high
        FROM tickets
    """).fetchone())

    recent = [
        row_to_dict(r)
        for r in db.execute(
            "SELECT ticket_id, customer_name, subject, status, priority, created_at FROM tickets ORDER BY created_at DESC LIMIT 5"
        ).fetchall()
    ]

    return jsonify({"stats": stats, "recent": recent})

# ─────────────────────────────────────────────
# Entry point
# ─────────────────────────────────────────────

if __name__ == "__main__":
    init_db()
    port = int(os.environ.get("PORT", 5000))
    debug = os.environ.get("FLASK_ENV") == "development"
    print(f"✅  SupportDesk CRM  →  http://localhost:{port}")
    app.run(host="0.0.0.0", port=port, debug=debug)
