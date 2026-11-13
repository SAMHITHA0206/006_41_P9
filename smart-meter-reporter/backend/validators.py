"""Part A: DFA + equivalent regular expression validation.

Meter ID : GRID [A-Z] [0-9]{3} [R|Y|B]      e.g. GRIDA123R
Reading  : [0-9]{5} . [0-9]{2} kWh          e.g. 01234.56kWh
"""
import re
import string

from config import PHASES

# Equivalent regular expressions (matched with fullmatch, so no anchors / trailing-newline issue)
METER_REGEX = re.compile(r"GRID[A-Z][0-9]{3}[RYB]")
READING_REGEX = re.compile(r"[0-9]{5}\.[0-9]{2}kWh")

DEAD = "dead"
UP, DG = string.ascii_uppercase, string.digits


class DFA:
    def __init__(self, name, start, accepting, delta, hints):
        self.name, self.start, self.accepting = name, start, set(accepting)
        self.delta, self.hints = delta, hints

    def run(self, text):
        state, path = self.start, [self.start]
        for i, ch in enumerate(text):
            nxt = self.delta.get((state, ch), DEAD)
            if nxt == DEAD:
                path.append(DEAD)
                return {"accepted": False, "fail_index": i, "state": state, "char": ch, "path": path}
            state = nxt
            path.append(state)
        ok = state in self.accepting
        return {"accepted": ok, "fail_index": None if ok else len(text),
                "state": state, "char": None, "path": path}

    def accepts(self, text):
        return self.run(text)["accepted"]


def _build_meter_dfa():
    d = {}
    for i, c in enumerate("GRID"):
        d[(f"q{i}", c)] = f"q{i+1}"
    for c in UP:
        d[("q4", c)] = "q5"                      # section letter
    for a, b in (("q5", "q6"), ("q6", "q7"), ("q7", "q8")):
        for c in DG:
            d[(a, c)] = b                        # three digits
    for c in PHASES:
        d[("q8", c)] = "q9"                      # phase -> accepting
    hints = {
        "q0": "'G' (meter IDs start with GRID)", "q1": "'R' (meter IDs start with GRID)",
        "q2": "'I' (meter IDs start with GRID)", "q3": "'D' (meter IDs start with GRID)",
        "q4": "one uppercase section letter A-Z",
        "q5": "a digit (exactly 3 digits required)", "q6": "a digit (exactly 3 digits required)",
        "q7": "a digit (exactly 3 digits required)",
        "q8": f"a phase letter ({', '.join(PHASES)})",
        "q9": "end of ID (no extra characters allowed)",
    }
    return DFA("meter_id", "q0", {"q9"}, d, hints)


def _build_reading_dfa():
    d = {}
    for i in range(5):
        for c in DG:
            d[(f"r{i}", c)] = f"r{i+1}"
    d[("r5", ".")] = "r6"
    for a, b in (("r6", "r7"), ("r7", "r8")):
        for c in DG:
            d[(a, c)] = b
    d[("r8", "k")], d[("r9", "W")], d[("r10", "h")] = "r9", "r10", "r11"
    hints = {f"r{i}": "a digit (5 digits before the decimal point)" for i in range(5)}
    hints.update({"r5": "'.' after the 5 digits", "r6": "a digit (2 decimal digits)",
                  "r7": "a digit (2 decimal digits)", "r8": "'k' (unit must be kWh)",
                  "r9": "'W' (unit must be kWh)", "r10": "'h' (unit must be kWh)",
                  "r11": "end of reading (no extra characters allowed)"})
    return DFA("reading", "r0", {"r11"}, d, hints)


METER_DFA = _build_meter_dfa()
READING_DFA = _build_reading_dfa()


def _validate(label, text, dfa, regex):
    if not isinstance(text, str) or not text.strip():
        return {"valid": False, "message": f"{label} is required", "dfa_accepted": False,
                "regex_accepted": False, "agree": True, "trace": []}
    res = dfa.run(text)
    rx = regex.fullmatch(text) is not None
    if res["accepted"]:
        msg = f"{label} is valid"
    else:
        hint = dfa.hints.get(res["state"], "valid input")
        if res["char"] is None:
            msg = f"{label} '{text}' is incomplete: expected {hint} but the input ended"
        else:
            msg = f"{label} '{text}' is invalid at position {res['fail_index']+1} ('{res['char']}'): expected {hint}"
    return {"valid": res["accepted"], "message": msg, "dfa_accepted": res["accepted"],
            "regex_accepted": rx, "agree": res["accepted"] == rx, "trace": res["path"]}


def validate_meter_id(text):
    return _validate("Meter ID", text, METER_DFA, METER_REGEX)


def validate_reading(text):
    return _validate("Reading", text, READING_DFA, READING_REGEX)
