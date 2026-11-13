"""Part B: routing table + dispatch algorithm.

Dispatch steps for a VALIDATED report:
 1. Extract routing key (section letter) from the meter ID.
 2. Look it up in the routing table (config.SECTIONS). Unknown key -> central correction queue.
 3. No category -> central correction queue (never silently classified).
 4. Walk crews in order: home crew, then nearest by section distance (tie -> earlier letter).
    First crew that is available AND below capacity gets the report.
      home crew -> DIRECT ; other crew -> ESCALATED_BACKUP
 5. Nobody eligible:
      P1 (emergency) -> PRIORITY_OVERRIDE: nearest *available* crew takes it even over capacity
      otherwise      -> WAITING queue
 6. Whenever capacity frees up (resolve / availability / capacity change) the WAITING queue is
    drained in deterministic order: priority ASC, created_at ASC, report id ASC.
 Assignment is a guarded UPDATE (only when status='Pending' AND assigned_crew IS NULL),
 so a report can never be assigned twice.
"""
from datetime import datetime, timezone

from config import QUEUE_CORRECTION, QUEUE_WAITING, SECTIONS

PRIORITY_LABELS = {1: "P1 Emergency", 2: "P2 High", 3: "P3 Medium", 4: "P4 Low"}
URGENCY_BASE = {"Critical": 1, "High": 2, "Medium": 3, "Low": 4}


def now():
    return datetime.now(timezone.utc).isoformat(timespec="microseconds")


def compute_priority(category, urgency):
    p = URGENCY_BASE.get(urgency, 4)
    if category in ("Tampering", "Outage"):
        p = min(p, 2)           # safety / revenue-critical categories are at least P2
    return p


def extract_routing_key(meter_id):
    """Only called on a validated meter ID: GRID<section><3 digits><phase>."""
    return meter_id[4]


def open_count(conn, crew_id):
    return conn.execute("SELECT COUNT(*) FROM reports WHERE assigned_crew=? AND status IN ('Assigned','In Progress')",
                        (crew_id,)).fetchone()[0]


def log(conn, rid, decision, detail):
    conn.execute("INSERT INTO routing_log(report_id,decision,detail,ts) VALUES(?,?,?,?)", (rid, decision, detail, now()))


def _ordered_crews(conn, key):
    crews = conn.execute("SELECT * FROM crews ORDER BY section").fetchall()
    home = next(i for i, c in enumerate(crews) if c["section"] == key)
    return sorted(enumerate(crews), key=lambda t: (abs(t[0] - home), t[0]))


def _assign(conn, r, crew, decision, note):
    cur = conn.execute(
        "UPDATE reports SET assigned_crew=?, status='Assigned', queue=NULL, routing_decision=?, routing_note=?, updated_at=? "
        "WHERE report_id=? AND status='Pending' AND assigned_crew IS NULL",
        (crew["id"], decision, note, now(), r["report_id"]))
    if cur.rowcount != 1:
        return False
    log(conn, r["report_id"], decision, note)
    return True


def _set_queue(conn, r, queue, decision, note):
    conn.execute("UPDATE reports SET queue=?, routing_decision=?, routing_note=?, updated_at=? WHERE report_id=?",
                 (queue, decision, note, now(), r["report_id"]))
    log(conn, r["report_id"], decision, note)


def _try_assign(conn, r, allow_override, from_queue=False):
    ordered = _ordered_crews(conn, r["routing_key"])
    home = ordered[0][1]
    suffix = " (dequeued from waiting queue)" if from_queue else ""
    for idx, c in ordered:
        if c["available"] and open_count(conn, c["id"]) < c["capacity"]:
            if idx == ordered[0][0]:
                decision, note = "DIRECT", f"Assigned to home crew {c['id']}{suffix}"
            else:
                why = "home crew unavailable" if not home["available"] else "home crew at capacity"
                decision, note = "ESCALATED_BACKUP", f"{why}; escalated to nearest available crew {c['id']}{suffix}"
            return decision if _assign(conn, r, c, decision, note) else None
    if allow_override and r["priority"] == 1:
        for idx, c in ordered:
            if c["available"]:
                note = (f"P1 emergency override: all crews full; {c['id']} takes it over capacity "
                        f"({open_count(conn, c['id'])}/{c['capacity']} open before this case)")
                return "PRIORITY_OVERRIDE" if _assign(conn, r, c, "PRIORITY_OVERRIDE", note) else None
    return None


def dispatch(conn, report_id):
    r = conn.execute("SELECT * FROM reports WHERE report_id=?", (report_id,)).fetchone()
    if r is None or r["validation_status"] != "VALID":
        raise ValueError("Only validated reports can be dispatched")
    if r["status"] != "Pending" or r["assigned_crew"]:
        return r["routing_decision"]                      # already handled -> no duplicate assignment

    key = r["routing_key"] or extract_routing_key(r["meter_id"])
    section = SECTIONS.get(key)
    conn.execute("UPDATE reports SET routing_key=?, zone=? WHERE report_id=?",
                 (key, section["zone"] if section else None, report_id))
    r = conn.execute("SELECT * FROM reports WHERE report_id=?", (report_id,)).fetchone()

    if section is None:
        _set_queue(conn, r, QUEUE_CORRECTION, "FALLBACK_UNKNOWN_ZONE",
                   f"Unknown routing key '{key}': sent to central correction queue")
        return "FALLBACK_UNKNOWN_ZONE"
    if not r["category"]:
        _set_queue(conn, r, QUEUE_CORRECTION, "FALLBACK_UNCLASSIFIED",
                   "No valid category: sent to central correction queue")
        return "FALLBACK_UNCLASSIFIED"

    decision = _try_assign(conn, r, allow_override=True)
    if decision:
        return decision
    _set_queue(conn, r, QUEUE_WAITING, "QUEUED",
               "All eligible crews unavailable or at capacity: placed in waiting queue")
    return "QUEUED"


def drain_queue(conn):
    rows = conn.execute("SELECT * FROM reports WHERE status='Pending' AND queue=? "
                        "ORDER BY priority ASC, created_at ASC, num ASC", (QUEUE_WAITING,)).fetchall()
    n = 0
    for r in rows:
        if _try_assign(conn, r, allow_override=False, from_queue=True):
            n += 1
    return n
