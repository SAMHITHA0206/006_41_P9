"""Item 13 demo: prints the full workflow on a throw-away database.  Run: python demo_workflow.py"""
import os
import tempfile

os.environ["SM_TESTING"] = "1"
import db

tmp = tempfile.NamedTemporaryFile(suffix=".db", delete=False)
tmp.close()
db.DB_PATH = tmp.name
db.init_db()
import app

c = app.app.test_client()


def show(title, r):
    j = r.get_json()
    rep = j.get("report", j)
    print(f"\n== {title}\n   id={rep.get('report_id')} validation={rep.get('validation_status')} category={rep.get('category')} "
          f"priority={rep.get('priority')} status={rep.get('status')} crew={rep.get('assigned_crew')} queue={rep.get('queue')}\n"
          f"   decision={rep.get('routing_decision')}: {rep.get('routing_note') or rep.get('validation_message')}")
    return rep


base = {"reporter_name": "Inspector Ravi", "reading": "01234.56kWh", "urgency": "High"}
show("1. Malformed ID is rejected before dispatch", c.post("/api/reports", json={**base, "meter_id": "GRIDA12R", "code": "TMP", "description": "seal cut"}))
r = show("2. Valid tampering report -> validation, classification, routing, assignment",
         c.post("/api/reports", json={**base, "meter_id": "GRIDB204Y", "code": "TMP", "description": "seal broken on meter"}))
show("3. Unknown zone -> correction queue", c.post("/api/reports", json={**base, "meter_id": "GRIDZ204Y", "code": "OUT", "description": "no power"}))
show("4. Status: In Progress", c.patch(f"/api/reports/{r['report_id']}/status", json={"status": "In Progress"}))
show("5. Status: Resolved", c.patch(f"/api/reports/{r['report_id']}/status", json={"status": "Resolved"}))
print("\nUser dashboard:", {k: v for k, v in c.get("/api/dashboard/user").get_json().items() if k != "recent"})
os.unlink(tmp.name)
