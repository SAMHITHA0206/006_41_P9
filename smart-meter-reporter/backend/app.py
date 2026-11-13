"""Flask API: validation -> classification -> routing -> status tracking as one workflow."""
import os

from flask import Flask, abort, jsonify, request, send_from_directory

import classifier
import db
import router
import validators
from config import CATEGORIES, NEXT_STATUS, SECTIONS, URGENCIES

app = Flask(__name__, static_folder=None)
DIST = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "frontend", "dist"))

if not os.environ.get("SM_TESTING"):
    db.init_db()


@app.after_request
def cors(resp):
    resp.headers["Access-Control-Allow-Origin"] = "*"
    resp.headers["Access-Control-Allow-Headers"] = "Content-Type"
    resp.headers["Access-Control-Allow-Methods"] = "GET,POST,PATCH,OPTIONS"
    return resp


@app.before_request
def preflight():
    if request.method == "OPTIONS":
        return ("", 204)


def body():
    return request.get_json(silent=True) or {}


def analyse(p):
    g = lambda k: str(p.get(k) or "").strip()
    name, meter, reading, code, desc, urgency = (g("reporter_name"), g("meter_id"), g("reading"),
                                                 g("code"), g("description"), g("urgency"))
    m, rd = validators.validate_meter_id(meter), validators.validate_reading(reading)
    errors = {}
    if not name:
        errors["reporter_name"] = "Reporter name is required"
    if not m["valid"]:
        errors["meter_id"] = m["message"]
    if not rd["valid"]:
        errors["reading"] = rd["message"]
    if urgency not in URGENCIES:
        errors["urgency"] = f"Urgency must be one of {', '.join(URGENCIES)}"
    if len(desc) < 5:
        errors["description"] = "Description must be at least 5 characters"
    cls = classifier.classify(code, desc)
    key = zone = crew = None
    if m["valid"]:
        key = router.extract_routing_key(meter)
        s = SECTIONS.get(key)
        zone, crew = (s["zone"], s["crew"]) if s else (None, None)
    prio = router.compute_priority(cls["category"], urgency) if urgency in URGENCIES else None
    return {"fields": {"reporter_name": name, "reporter_contact": g("reporter_contact"), "meter_id": meter,
                       "reading": reading, "code": code.upper(), "description": desc, "urgency": urgency},
            "errors": errors, "meter": m, "reading": rd, "classification": cls, "priority": prio,
            "priority_label": router.PRIORITY_LABELS.get(prio), "routing_key": key, "zone": zone, "crew": crew}


def fetch(conn, rid):
    r = conn.execute("SELECT * FROM reports WHERE report_id=?", (rid.upper(),)).fetchone()
    return dict(r) if r else None


@app.post("/api/validate")
def validate_preview():
    a = analyse(body())
    a.pop("fields")
    return jsonify(a)


@app.post("/api/reports")
def submit():
    a = analyse(body())
    f, ts = a["fields"], router.now()
    with db.tx() as conn:
        cols = "reporter_name,reporter_contact,meter_id,reading,code,description,urgency,validation_status," \
               "validation_message,category,classification_note,priority,routing_key,zone,status,created_at,updated_at"
        if a["errors"]:
            vals = (f["reporter_name"], f["reporter_contact"], f["meter_id"], f["reading"], f["code"], f["description"],
                    f["urgency"], "REJECTED", "; ".join(a["errors"].values()), None, None, None, None, None,
                    "Rejected", ts, ts)
        else:
            c = a["classification"]
            vals = (f["reporter_name"], f["reporter_contact"], f["meter_id"], f["reading"], f["code"], f["description"],
                    f["urgency"], "VALID", "Meter ID and reading accepted by DFA and regex", c["category"], c["message"],
                    a["priority"], a["routing_key"], a["zone"], "Pending", ts, ts)
        cur = conn.execute(f"INSERT INTO reports({cols}) VALUES({','.join('?' * 17)})", vals)
        rid = f"RPT-{cur.lastrowid:06d}"
        conn.execute("UPDATE reports SET report_id=? WHERE num=?", (rid, cur.lastrowid))
        if a["errors"]:
            router.log(conn, rid, "REJECTED", "; ".join(a["errors"].values()))
            return jsonify({"report": fetch(conn, rid), "errors": a["errors"]}), 422
        router.dispatch(conn, rid)
        return jsonify({"report": fetch(conn, rid), "errors": {}}), 201


@app.get("/api/reports/<rid>")
def get_report(rid):
    with db.db() as conn:
        r = fetch(conn, rid)
        if not r:
            return jsonify({"error": f"Report {rid} not found"}), 404
        r["log"] = [dict(x) for x in conn.execute("SELECT * FROM routing_log WHERE report_id=? ORDER BY id", (r["report_id"],))]
        return jsonify(r)


@app.get("/api/reports")
def list_reports():
    q, args = "SELECT * FROM reports WHERE 1=1", []
    for param, col in (("crew", "assigned_crew"), ("status", "status"), ("queue", "queue")):
        if request.args.get(param):
            q += f" AND {col}=?"
            args.append(request.args[param])
    q += " ORDER BY priority IS NULL, priority ASC, created_at ASC, num ASC LIMIT 500"
    with db.db() as conn:
        return jsonify([dict(r) for r in conn.execute(q, args)])


@app.patch("/api/reports/<rid>/status")
def update_status(rid):
    new = body().get("status")
    with db.tx() as conn:
        r = fetch(conn, rid)
        if not r:
            return jsonify({"error": "Report not found"}), 404
        if NEXT_STATUS.get(r["status"]) != new:
            return jsonify({"error": f"Invalid transition {r['status']} -> {new}. "
                                     "Allowed: Assigned -> In Progress -> Resolved"}), 400
        conn.execute("UPDATE reports SET status=?, updated_at=? WHERE report_id=?", (new, router.now(), r["report_id"]))
        router.log(conn, r["report_id"], "STATUS", f"{r['status']} -> {new}")
        if new == "Resolved":
            router.drain_queue(conn)
        return jsonify(fetch(conn, r["report_id"]))


@app.post("/api/reports/<rid>/correct")
def correct(rid):
    """Manager fixes a report in the correction queue (set category and/or section) and re-dispatches it."""
    b = body()
    with db.tx() as conn:
        r = fetch(conn, rid)
        if not r:
            return jsonify({"error": "Report not found"}), 404
        if r["queue"] != "CORRECTION" or r["status"] != "Pending":
            return jsonify({"error": "Report is not in the correction queue"}), 400
        cat, sec = b.get("category") or r["category"], (b.get("section") or r["routing_key"] or "").upper()
        if cat and cat not in CATEGORIES:
            return jsonify({"error": f"Category must be one of {', '.join(CATEGORIES)}"}), 400
        if sec not in SECTIONS:
            return jsonify({"error": f"Section must be one of {', '.join(SECTIONS)}"}), 400
        conn.execute("UPDATE reports SET category=?, routing_key=?, priority=?, queue=NULL, updated_at=? WHERE report_id=?",
                     (cat, sec, router.compute_priority(cat, r["urgency"]), router.now(), r["report_id"]))
        router.log(conn, r["report_id"], "CORRECTED", f"category={cat}, section={sec}")
        router.dispatch(conn, r["report_id"])
        return jsonify(fetch(conn, r["report_id"]))


def crew_rows(conn):
    out = []
    for c in conn.execute("SELECT * FROM crews ORDER BY section"):
        d = dict(c)
        d["open_cases"] = router.open_count(conn, c["id"])
        d["available"] = bool(d["available"])
        out.append(d)
    return out


@app.get("/api/crews")
def crews():
    with db.db() as conn:
        return jsonify(crew_rows(conn))


@app.patch("/api/crews/<cid>")
def update_crew(cid):
    b = body()
    with db.tx() as conn:
        c = conn.execute("SELECT * FROM crews WHERE id=?", (cid,)).fetchone()
        if not c:
            return jsonify({"error": "Crew not found"}), 404
        cap, avail = b.get("capacity", c["capacity"]), b.get("available", bool(c["available"]))
        if not isinstance(cap, int) or isinstance(cap, bool) or not 1 <= cap <= 20:
            return jsonify({"error": "Capacity must be an integer from 1 to 20"}), 400
        conn.execute("UPDATE crews SET capacity=?, available=? WHERE id=?", (cap, 1 if avail else 0, cid))
        router.log(conn, "-", "CREW", f"{cid}: capacity={cap}, available={bool(avail)}")
        router.drain_queue(conn)
        return jsonify([c for c in crew_rows(conn) if c["id"] == cid][0])


@app.get("/api/routing")
def routing():
    with db.db() as conn:
        table = [{"key": k, **v} for k, v in SECTIONS.items()]
        rows = lambda q, a=(): [dict(r) for r in conn.execute(q, a)]
        return jsonify({
            "table": table,
            "fallback": "CENTRAL-CORRECTION-QUEUE",
            "loads": crew_rows(conn),
            "backups": rows("SELECT * FROM reports WHERE routing_decision IN ('ESCALATED_BACKUP','PRIORITY_OVERRIDE') ORDER BY num DESC LIMIT 50"),
            "waiting": rows("SELECT * FROM reports WHERE status='Pending' AND queue='WAITING' ORDER BY priority, created_at, num"),
            "correction": rows("SELECT * FROM reports WHERE status='Pending' AND queue='CORRECTION' ORDER BY priority IS NULL, priority, created_at, num"),
            "decisions": rows("SELECT * FROM routing_log ORDER BY id DESC LIMIT 60"),
        })


@app.get("/api/dashboard/user")
def user_dashboard():
    with db.db() as conn:
        n = lambda w: conn.execute(f"SELECT COUNT(*) FROM reports WHERE {w}").fetchone()[0]
        return jsonify({"total": n("1=1"), "pending": n("status='Pending'"),
                        "assigned": n("status IN ('Assigned','In Progress')"),
                        "resolved": n("status='Resolved'"), "rejected": n("status='Rejected'"),
                        "recent": [dict(r) for r in conn.execute("SELECT * FROM reports ORDER BY num DESC LIMIT 8")]})


@app.get("/api/analytics")
def analytics():
    with db.db() as conn:
        def grp(col, label, where="validation_status='VALID'"):
            return [{"name": r["k"], "count": r["n"]} for r in conn.execute(
                f"SELECT COALESCE({col},'{label}') k, COUNT(*) n FROM reports WHERE {where} GROUP BY k ORDER BY k")]
        n = lambda w: conn.execute(f"SELECT COUNT(*) FROM reports WHERE {w}").fetchone()[0]
        return jsonify({"by_zone": grp("zone", "Unrouted"), "by_category": grp("category", "Unclassified"),
                        "by_priority": grp("priority", "n/a"), "by_status": grp("status", "n/a", "1=1"),
                        "resolved": n("status='Resolved'"),
                        "unresolved": n("validation_status='VALID' AND status!='Resolved'"),
                        "rejected": n("status='Rejected'")})


@app.route("/", defaults={"path": ""})
@app.route("/<path:path>")
def spa(path):
    if path.startswith("api"):
        abort(404)
    if path and os.path.exists(os.path.join(DIST, path)):
        return send_from_directory(DIST, path)
    if os.path.exists(os.path.join(DIST, "index.html")):
        return send_from_directory(DIST, "index.html")
    return "API running. Build the frontend (npm run build) or use the Vite dev server.", 200


if __name__ == "__main__":
    app.run(host="0.0.0.0", port=int(os.environ.get("PORT", 5000)), debug=False)
