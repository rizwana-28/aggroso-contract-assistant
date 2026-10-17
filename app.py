import os
import re
import sqlite3
from datetime import datetime, date
from flask import Flask, request, jsonify, render_template, g

APP_DIR = os.path.dirname(os.path.abspath(__file__))
DB_PATH = os.environ.get("DATABASE_PATH", os.path.join(APP_DIR, "contracts.db"))
app = Flask(__name__)
app.config["MAX_CONTENT_LENGTH"] = 2 * 1024 * 1024

SCHEMA = """
CREATE TABLE IF NOT EXISTS contracts (
 id INTEGER PRIMARY KEY AUTOINCREMENT,
 title TEXT NOT NULL,
 counterparty TEXT DEFAULT '',
 contract_text TEXT NOT NULL,
 created_at TEXT NOT NULL
);
CREATE TABLE IF NOT EXISTS obligations (
 id INTEGER PRIMARY KEY AUTOINCREMENT,
 contract_id INTEGER NOT NULL,
 description TEXT NOT NULL,
 due_date TEXT DEFAULT '',
 category TEXT NOT NULL,
 confidence REAL NOT NULL DEFAULT 0.5,
 status TEXT NOT NULL DEFAULT 'Needs review',
 reviewer_note TEXT DEFAULT '',
 created_at TEXT NOT NULL,
 FOREIGN KEY(contract_id) REFERENCES contracts(id)
);
"""

def db():
    if "db" not in g:
        g.db = sqlite3.connect(DB_PATH)
        g.db.row_factory = sqlite3.Row
        g.db.execute("PRAGMA foreign_keys = ON")
    return g.db

@app.teardown_appcontext
def close_db(_error):
    conn = g.pop("db", None)
    if conn is not None:
        conn.close()

def init_db():
    conn = sqlite3.connect(DB_PATH)
    conn.executescript(SCHEMA)
    conn.commit()
    conn.close()

def extract_obligations(text):
    """Rule-based extraction aid. Results are suggestions and require human review."""
    patterns = [
        ("Renewal", r".{0,100}(?:renew(?:al|s|ed)?|extend(?:s|ed|ion)?|auto[- ]?renew).{0,180}"),
        ("Payment", r".{0,100}(?:payment|invoice|payable|fee|within\s+\d+\s+days).{0,180}"),
        ("Notice", r".{0,100}(?:notice|notify|written notification|termination notice).{0,180}"),
        ("Delivery / service", r".{0,100}(?:deliver(?:y|ies)?|provide services|service level|milestone).{0,180}"),
        ("Compliance", r".{0,100}(?:comply|compliance|confidentiality|data protection|audit).{0,180}"),
    ]
    found = []
    seen = set()
    for category, pattern in patterns:
        for match in re.finditer(pattern, text, flags=re.IGNORECASE | re.DOTALL):
            snippet = re.sub(r"\s+", " ", match.group(0)).strip(" \n\t.;")
            key = (category, snippet.lower())
            if len(snippet) >= 18 and key not in seen:
                seen.add(key)
                found.append({
                    "description": snippet[:280],
                    "category": category,
                    "due_date": find_date(snippet),
                    "confidence": 0.65 if find_date(snippet) else 0.45,
                    "status": "Needs review"
                })
    # If no keywords matched, still give a transparent review task rather than claiming nothing exists.
    if not found:
        found.append({
            "description": "Review the contract manually and add any obligations, deadlines, notice periods, or renewal terms.",
            "category": "Manual review",
            "due_date": "",
            "confidence": 0.2,
            "status": "Needs review"
        })
    return found[:30]

def find_date(text):
    # Deliberately supports only unambiguous numeric/English dates; ambiguous formats are not guessed.
    patterns = [
        (r"\b(20\d{2})-(0[1-9]|1[0-2])-([0-2]\d|3[01])\b", "%Y-%m-%d"),
        (r"\b(January|February|March|April|May|June|July|August|September|October|November|December)\s+([0-3]?\d),?\s+(20\d{2})\b", "%B %d %Y"),
    ]
    for pattern, fmt in patterns:
        m = re.search(pattern, text, flags=re.IGNORECASE)
        if m:
            raw = m.group(0).replace(",", "")
            try:
                return datetime.strptime(raw.title(), fmt).date().isoformat()
            except ValueError:
                pass
    return ""

@app.route("/")
def index():
    return render_template("index.html")

@app.route("/api/contracts", methods=["GET", "POST"])
def contracts():
    conn = db()
    if request.method == "GET":
        rows = conn.execute("SELECT * FROM contracts ORDER BY id DESC").fetchall()
        return jsonify([dict(r) for r in rows])
    data = request.get_json(silent=True) or {}
    title = (data.get("title") or "").strip()
    text = (data.get("contract_text") or "").strip()
    counterparty = (data.get("counterparty") or "").strip()
    if not title or len(text) < 30:
        return jsonify({"error": "Enter a contract title and at least 30 characters of contract text."}), 400
    now = datetime.utcnow().isoformat(timespec="seconds") + "Z"
    cur = conn.execute(
        "INSERT INTO contracts(title,counterparty,contract_text,created_at) VALUES(?,?,?,?)",
        (title[:160], counterparty[:160], text[:100000], now)
    )
    contract_id = cur.lastrowid
    suggestions = extract_obligations(text)
    for item in suggestions:
        conn.execute("""INSERT INTO obligations
            (contract_id,description,due_date,category,confidence,status,created_at)
            VALUES(?,?,?,?,?,?,?)""",
            (contract_id, item["description"], item["due_date"], item["category"],
             item["confidence"], item["status"], now))
    conn.commit()
    return jsonify({"id": contract_id, "suggestions_created": len(suggestions)}), 201

@app.route("/api/obligations", methods=["GET"])
def obligations():
    rows = db().execute("""SELECT o.*, c.title AS contract_title, c.counterparty
        FROM obligations o JOIN contracts c ON c.id=o.contract_id
        ORDER BY CASE WHEN o.due_date='' THEN 1 ELSE 0 END, o.due_date ASC, o.id DESC""").fetchall()
    return jsonify([dict(r) for r in rows])

@app.route("/api/obligations/<int:oid>", methods=["PATCH"])
def update_obligation(oid):
    data = request.get_json(silent=True) or {}
    status = data.get("status")
    note = (data.get("reviewer_note") or "").strip()[:1000]
    due_date = (data.get("due_date") or "").strip()
    description = (data.get("description") or "").strip()[:280]
    allowed = {"Needs review", "Approved", "Rejected"}
    if status not in allowed:
        return jsonify({"error": "Choose Needs review, Approved, or Rejected."}), 400
    if due_date:
        try:
            date.fromisoformat(due_date)
        except ValueError:
            return jsonify({"error": "Due date must use YYYY-MM-DD."}), 400
    cur = db().execute("""UPDATE obligations SET status=?, reviewer_note=?,
        due_date=?, description=? WHERE id=?""",
        (status, note, due_date, description or "Manual review required", oid))
    db().commit()
    if cur.rowcount == 0:
        return jsonify({"error": "Obligation not found."}), 404
    return jsonify({"ok": True})

@app.route("/api/health")
def health():
    return jsonify({"status": "ok", "app": "Contract Obligation and Renewal Assistant"})

@app.errorhandler(413)
def too_large(_error):
    return jsonify({"error": "Request too large. Please use contract text under 2 MB."}), 413

init_db()

if __name__ == "__main__":
    app.run(host="0.0.0.0", port=int(os.environ.get("PORT", "5000")), debug=False)
