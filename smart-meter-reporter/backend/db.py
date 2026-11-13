"""SQLite storage."""
import os
import sqlite3
import threading
from contextlib import contextmanager

from config import CREW_CAPACITY, SECTIONS

DB_PATH = os.environ.get("SMART_METER_DB", os.path.join(os.path.dirname(os.path.abspath(__file__)), "smartmeter.db"))
LOCK = threading.RLock()   # serialises writes -> deterministic ordering, no duplicate assignment

SCHEMA = """
CREATE TABLE IF NOT EXISTS crews(
  id TEXT PRIMARY KEY, section TEXT UNIQUE NOT NULL, name TEXT NOT NULL, zone TEXT NOT NULL,
  depot TEXT NOT NULL, capacity INTEGER NOT NULL, available INTEGER NOT NULL DEFAULT 1);
CREATE TABLE IF NOT EXISTS reports(
  num INTEGER PRIMARY KEY AUTOINCREMENT, report_id TEXT UNIQUE,
  reporter_name TEXT, reporter_contact TEXT, meter_id TEXT, reading TEXT, code TEXT,
  description TEXT, urgency TEXT,
  validation_status TEXT NOT NULL, validation_message TEXT,
  category TEXT, classification_note TEXT, priority INTEGER,
  routing_key TEXT, zone TEXT, assigned_crew TEXT, status TEXT NOT NULL,
  queue TEXT, routing_decision TEXT, routing_note TEXT,
  created_at TEXT NOT NULL, updated_at TEXT NOT NULL);
CREATE TABLE IF NOT EXISTS routing_log(
  id INTEGER PRIMARY KEY AUTOINCREMENT, report_id TEXT, decision TEXT, detail TEXT, ts TEXT);
"""


def connect():
    conn = sqlite3.connect(DB_PATH, check_same_thread=False, timeout=10)
    conn.row_factory = sqlite3.Row
    return conn


@contextmanager
def db():
    conn = connect()
    try:
        yield conn
        conn.commit()
    except Exception:
        conn.rollback()
        raise
    finally:
        conn.close()


@contextmanager
def tx():
    """Write transaction guarded by the global lock."""
    with LOCK:
        with db() as conn:
            yield conn


def init_db():
    with tx() as conn:
        conn.executescript(SCHEMA)
        if conn.execute("SELECT COUNT(*) FROM crews").fetchone()[0] == 0:
            for sec, s in SECTIONS.items():
                conn.execute("INSERT INTO crews(id,section,name,zone,depot,capacity,available) VALUES(?,?,?,?,?,?,1)",
                             (s["crew"], sec, s["name"], s["zone"], s["depot"], CREW_CAPACITY))
