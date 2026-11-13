# Smart Meter Anomaly Reporter (BCS503 + BCS502)

Parts C and D: React frontend + Flask backend + SQLite, with Parts A/B logic built in.

> **Stack note:** Question 8 says MERN, but Question 10 explicitly says *Flask backend and SQLite*.
> This project follows Q10 (React + Flask + SQLite). Mention this to your faculty in the viva:
> the React part of MERN is kept; Express/MongoDB are replaced by Flask/SQLite as Q10 requires.

## Structure
```
backend/   config.py  validators.py (DFA+regex)  classifier.py  router.py (routing table + dispatch)
           db.py  app.py (API)  test_smart_meter.py (21 tests)  demo_workflow.py
frontend/  Vite + React (5 pages)
```

## Run it (3 steps)
**1. Backend**
```bash
cd backend
python -m venv venv
venv\Scripts\activate          # Windows   (Mac/Linux: source venv/bin/activate)
pip install -r requirements.txt
python -m unittest -v test_smart_meter     # Part D: 21 tests, all should pass
python demo_workflow.py                    # Item 13: prints the full workflow
python app.py                              # API on http://localhost:5000
```
**2. Frontend** (new terminal; needs Node 18+)
```bash
cd frontend
npm install
npm run dev                                # http://localhost:5173  (proxies /api to :5000)
```
**3. Deploy (single service)**: `cd frontend && npm run build`, then run `gunicorn app:app` from `backend/`.
Flask serves `frontend/dist`. On Render: Build `pip install -r backend/requirements.txt && cd frontend && npm install && npm run build`,
Start `cd backend && gunicorn app:app`. (SQLite resets on free hosts' redeploys; fine for a demo.)

## Key rules (be ready to explain)
- **Meter ID** `GRID[A-Z][0-9]{3}[RYB]`; **reading** `[0-9]{5}\.[0-9]{2}kWh`. DFA is the source of truth, regex cross-checks.
- **Routing key** = section letter (A-E). Letter outside A-E is a valid ID but unknown zone -> central correction queue.
- **Classification**: code (TMP/OUT/OVR/HWF/COM) + description keywords. Unknown code or no match -> NO category, correction queue.
  Conflict priority: Tampering > Outage > Hardware > Communication > Overconsumption.
- **Priority**: Critical=P1, High=P2, Medium=P3, Low=P4; Tampering/Outage are at least P2.
- **Capacity** 6 open cases (Assigned + In Progress) per crew. Overflow/unavailable -> nearest crew (tie -> earlier letter).
- **P1 override**: if every crew is full, nearest available crew takes it over capacity.
- **Waiting queue** order: priority, then submit time, then ID. Drained automatically when a case resolves or a crew's availability/capacity changes.
- **No duplicate assignment**: guarded UPDATE (`status='Pending' AND assigned_crew IS NULL`) + global write lock.

## Screens -> Q9
Submit Report (9a) · My Reports (9b) · Handler (9c) · Routing (9d) · Analytics (9e).
