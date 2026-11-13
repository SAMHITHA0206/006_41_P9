"""Part A: classify an accepted report into exactly five categories.

Rules (deterministic):
1. Candidates come from the report code (TMP/OUT/OVR/HWF/COM) AND keyword patterns in the description.
2. If a code is supplied but is not in CODE_MAP -> UNMAPPED_CODE: NO category is assigned
   (never silently defaulted); the report goes to the correction queue.
3. If several categories are candidates, the fixed PRIORITY_ORDER picks the winner.
4. No candidate at all -> NO_MATCH: no category, correction queue.
"""
import re

CODE_MAP = {"TMP": "Tampering", "OUT": "Outage", "OVR": "Overconsumption",
            "HWF": "Hardware", "COM": "Communication"}

# Highest priority first: safety/revenue-critical categories win conflicts.
PRIORITY_ORDER = ["Tampering", "Outage", "Hardware", "Communication", "Overconsumption"]

KEYWORDS = {
    "Tampering": r"tamper|bypass|seal\s+(broken|cut|removed)|magnet|illegal|hooking|theft|stolen",
    "Outage": r"outage|power\s*cut|no\s+power|blackout|supply\s+(failure|down)|no\s+electricity",
    "Overconsumption": r"overconsum|high\s+(usage|consumption)|spike|abnormal\s+usage|excess",
    "Hardware": r"display|burnt|burned|damaged|faulty|broken|hardware|battery|dead\s+meter|sparking",
    "Communication": r"communication|network|signal|gsm|no\s+data|offline|not\s+reporting|connectivity",
}


def classify(code, description):
    code = (code or "").strip().upper()
    desc = (description or "").lower()
    candidates, sources = set(), {}

    if code:
        if code not in CODE_MAP:
            return {"category": None, "status": "UNMAPPED_CODE", "candidates": [],
                    "message": f"Unknown report code '{code}'. Valid codes: {', '.join(CODE_MAP)}. "
                               "Sent to the correction queue; no category assigned."}
        candidates.add(CODE_MAP[code])
        sources[CODE_MAP[code]] = f"code {code}"

    for cat, pattern in KEYWORDS.items():
        if re.search(pattern, desc):
            candidates.add(cat)
            sources.setdefault(cat, "description keyword")

    if not candidates:
        return {"category": None, "status": "NO_MATCH", "candidates": [],
                "message": "No category code or keyword matched. Sent to the correction queue."}

    winner = next(c for c in PRIORITY_ORDER if c in candidates)
    ordered = [c for c in PRIORITY_ORDER if c in candidates]
    note = f"Classified as {winner} ({sources[winner]})"
    if len(ordered) > 1:
        note += f". Conflict between {', '.join(ordered)}; resolved by priority order " \
                f"{' > '.join(PRIORITY_ORDER)}"
    return {"category": winner, "status": "OK", "candidates": ordered, "message": note}
