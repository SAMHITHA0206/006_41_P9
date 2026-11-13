"""Part D: 21 test cases. Run:  python -m unittest -v test_smart_meter"""
import os
os.environ["SM_TESTING"] = "1"

import random
import sqlite3
import tempfile
import unittest

import db
import router
import validators as v
import classifier

import app as appmod


class Base(unittest.TestCase):
    def setUp(self):
        t = tempfile.NamedTemporaryFile(suffix=".db", delete=False)
        t.close()
        self.path = t.name
        db.DB_PATH = self.path
        db.init_db()
        self.c = appmod.app.test_client()

    def tearDown(self):
        os.unlink(self.path)

    def submit(self, meter="GRIDA123R", code="OVR", desc="High usage spike", urgency="Low",
               reading="01234.56kWh", name="Ravi"):
        r = self.c.post("/api/reports", json={"reporter_name": name, "meter_id": meter, "reading": reading,
                                              "code": code, "description": desc, "urgency": urgency})
        return r.status_code, r.get_json()["report"]

    def fill(self, letter, n):
        return [self.submit(meter=f"GRID{letter}{100+i}R")[1] for i in range(n)]

    def fill_all(self):
        out = {}
        for L in "ABCDE":
            out[L] = self.fill(L, 6)
        return out

    def advance(self, rid, to):
        return self.c.patch(f"/api/reports/{rid}/status", json={"status": to})

    def resolve(self, rid):
        self.advance(rid, "In Progress")
        return self.advance(rid, "Resolved")


class PartA(Base):
    VALID = ["GRIDA123R", "GRIDE999Y", "GRIDZ000B"]
    INVALID = ["", "GRID", "GRIDA12R", "GRIDA1234R", "GRIDa123R", "GRIDA123X", "GRIDA123RR", "grida123r",
               "GRID1123R", "XRIDA123R", "GRIDA123R\n"]

    def test_01_valid_meter_ids_dfa_and_regex(self):
        for s in self.VALID:
            self.assertTrue(v.METER_DFA.accepts(s) and v.METER_REGEX.fullmatch(s), s)

    def test_02_invalid_meter_ids_dfa_and_regex(self):
        for s in self.INVALID:
            self.assertFalse(v.METER_DFA.accepts(s), s)
            self.assertIsNone(v.METER_REGEX.fullmatch(s), s)

    def test_03_reading_valid_invalid_agreement(self):
        good = ["00000.00kWh", "12345.67kWh"]
        bad = ["1234.56kWh", "123456.78kWh", "12345.6kWh", "12345.67kwh", "12345,67kWh", "12345.67", "12345.67kWhx"]
        for s in good:
            self.assertTrue(v.validate_reading(s)["valid"] and v.validate_reading(s)["agree"])
        for s in bad:
            r = v.validate_reading(s)
            self.assertFalse(r["valid"], s)
            self.assertTrue(r["agree"], s)

    def test_04_fuzz_dfa_regex_agreement(self):
        random.seed(42)
        alpha = "GRIDAEZ0123456789RYBkWh. "
        for _ in range(3000):
            s = "".join(random.choice(alpha) for _ in range(random.randint(0, 12)))
            self.assertEqual(v.METER_DFA.accepts(s), v.METER_REGEX.fullmatch(s) is not None, s)
            self.assertEqual(v.READING_DFA.accepts(s), v.READING_REGEX.fullmatch(s) is not None, s)

    def test_05_meaningful_error_messages(self):
        self.assertIn("position 9", v.validate_meter_id("GRIDA123X")["message"])
        self.assertIn("incomplete", v.validate_meter_id("GRIDA12")["message"])
        self.assertIn("required", v.validate_meter_id("")["message"])

    def test_06_all_five_categories(self):
        for code, cat in [("TMP", "Tampering"), ("OUT", "Outage"), ("OVR", "Overconsumption"),
                          ("HWF", "Hardware"), ("COM", "Communication")]:
            self.assertEqual(classifier.classify(code, "report")["category"], cat)

    def test_07_conflicting_patterns_use_priority_rule(self):
        r = classifier.classify("OVR", "meter tampered and display broken")
        self.assertEqual(r["category"], "Tampering")
        self.assertIn("Conflict", r["message"])
        self.assertEqual(classifier.classify("", "signal lost, no power")["category"], "Outage")

    def test_08_unmapped_code_not_silently_classified(self):
        status, r = self.submit(code="ZZZ", desc="overconsumption spike")
        self.assertEqual(status, 201)
        self.assertIsNone(r["category"])
        self.assertEqual(r["queue"], "CORRECTION")
        self.assertEqual(r["status"], "Pending")

    def test_09_no_match_goes_to_correction_queue(self):
        _, r = self.submit(code="", desc="something odd happened")
        self.assertIsNone(r["category"])
        self.assertEqual(r["routing_decision"], "FALLBACK_UNCLASSIFIED")


class PartB(Base):
    def test_10_unknown_zone_fallback(self):
        _, r = self.submit(meter="GRIDZ123R")
        self.assertEqual(r["routing_decision"], "FALLBACK_UNKNOWN_ZONE")
        self.assertEqual(r["queue"], "CORRECTION")
        self.assertIsNone(r["assigned_crew"])

    def test_11_malformed_rejected_with_reason_and_stored(self):
        status, r = self.submit(meter="GRIDA12R")
        self.assertEqual(status, 422)
        self.assertEqual(r["validation_status"], "REJECTED")
        self.assertIn("position 8", r["validation_message"])
        self.assertIsNone(r["assigned_crew"])
        self.assertEqual(self.c.get(f"/api/reports/{r['report_id']}").status_code, 200)

    def test_12_direct_assignment_to_home_crew(self):
        _, r = self.submit(meter="GRIDC123Y")
        self.assertEqual((r["assigned_crew"], r["routing_decision"], r["status"]), ("CREW-C", "DIRECT", "Assigned"))
        self.assertEqual(r["zone"], "Central Grid")

    def test_13_capacity_overflow_escalates_to_nearest(self):
        self.fill("A", 6)
        _, r = self.submit(meter="GRIDA900R")
        self.assertEqual((r["assigned_crew"], r["routing_decision"]), ("CREW-B", "ESCALATED_BACKUP"))

    def test_14_unavailable_handler_uses_backup(self):
        self.c.patch("/api/crews/CREW-C", json={"available": False})
        _, r = self.submit(meter="GRIDC123R")
        self.assertEqual((r["assigned_crew"], r["routing_decision"]), ("CREW-B", "ESCALATED_BACKUP"))

    def test_15_all_full_waits_then_drains_on_resolve(self):
        f = self.fill_all()
        _, w = self.submit(meter="GRIDA500R")
        self.assertEqual((w["status"], w["queue"]), ("Pending", "WAITING"))
        self.resolve(f["C"][0]["report_id"])
        got = self.c.get(f"/api/reports/{w['report_id']}").get_json()
        self.assertEqual((got["status"], got["assigned_crew"]), ("Assigned", "CREW-C"))

    def test_16_priority_override_exceeds_capacity(self):
        self.fill_all()
        _, r = self.submit(meter="GRIDB800R", code="OUT", desc="feeder down", urgency="Critical")
        self.assertEqual((r["priority"], r["routing_decision"], r["assigned_crew"]), (1, "PRIORITY_OVERRIDE", "CREW-B"))
        crew = next(c for c in self.c.get("/api/crews").get_json() if c["id"] == "CREW-B")
        self.assertEqual(crew["open_cases"], 7)

    def test_17_deterministic_queue_ordering(self):
        f = self.fill_all()
        _, low = self.submit(meter="GRIDA501R", urgency="Low")
        _, high = self.submit(meter="GRIDA502R", urgency="High")
        _, med = self.submit(meter="GRIDA503R", urgency="Medium")
        self.resolve(f["A"][0]["report_id"])
        s = lambda r: self.c.get(f"/api/reports/{r['report_id']}").get_json()["status"]
        self.assertEqual((s(high), s(med), s(low)), ("Assigned", "Pending", "Pending"))
        self.resolve(f["A"][1]["report_id"])
        self.assertEqual((s(med), s(low)), ("Assigned", "Pending"))

    def test_18_no_duplicate_assignment(self):
        _, r = self.submit(meter="GRIDD123R")
        with db.tx() as conn:
            router.dispatch(conn, r["report_id"])
            router.dispatch(conn, r["report_id"])
        with db.db() as conn:
            n = conn.execute("SELECT COUNT(*) FROM routing_log WHERE report_id=? AND decision='DIRECT'", (r["report_id"],)).fetchone()[0]
            self.assertEqual(n, 1)
            self.assertEqual(router.open_count(conn, "CREW-D"), 1)

    def test_19_status_transitions(self):
        _, r = self.submit()
        rid = r["report_id"]
        self.assertEqual(self.advance(rid, "Resolved").status_code, 400)       # cannot skip
        self.assertEqual(self.advance(rid, "In Progress").status_code, 200)
        self.assertEqual(self.advance(rid, "Assigned").status_code, 400)       # cannot go back
        self.assertEqual(self.advance(rid, "Resolved").status_code, 200)
        self.assertEqual(self.advance(rid, "Resolved").status_code, 400)

    def test_20_correction_queue_fix_and_redispatch(self):
        _, r = self.submit(meter="GRIDZ123R", code="", desc="odd thing")
        fixed = self.c.post(f"/api/reports/{r['report_id']}/correct", json={"category": "Hardware", "section": "E"}).get_json()
        self.assertEqual((fixed["assigned_crew"], fixed["category"], fixed["status"]), ("CREW-E", "Hardware", "Assigned"))


class PartD(Base):
    def test_21_end_to_end_workflow_and_persistence(self):
        status, r = self.submit(meter="GRIDB204Y", code="TMP", desc="seal broken near feeder", urgency="High")
        self.assertEqual(status, 201)
        self.assertEqual((r["category"], r["priority"], r["assigned_crew"], r["status"]), ("Tampering", 2, "CREW-B", "Assigned"))
        self.advance(r["report_id"], "In Progress")
        self.advance(r["report_id"], "Resolved")
        raw = sqlite3.connect(self.path)                    # independent connection => really persisted
        row = raw.execute("SELECT status, category, validation_status, routing_decision FROM reports WHERE report_id=?",
                          (r["report_id"],)).fetchone()
        raw.close()
        self.assertEqual(row, ("Resolved", "Tampering", "VALID", "DIRECT"))
        self.assertEqual(self.c.get("/api/dashboard/user").get_json()["resolved"], 1)
        self.assertEqual(self.c.get("/api/analytics").get_json()["resolved"], 1)


if __name__ == "__main__":
    unittest.main(verbosity=2)
