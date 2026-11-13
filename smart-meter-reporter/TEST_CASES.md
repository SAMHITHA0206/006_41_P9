# Test cases (run: `python -m unittest -v test_smart_meter`)

| # | Area | Input / scenario | Expected |
|---|------|------------------|----------|
| 01 | Valid input | GRIDA123R, GRIDE999Y, GRIDZ000B | DFA and regex both accept |
| 02 | Invalid input | empty, GRID, GRIDA12R, GRIDA1234R, GRIDa123R, GRIDA123X, extra char, newline... | DFA and regex both reject |
| 03 | Reading | valid and 7 invalid readings | Correct verdict, DFA == regex |
| 04 | Agreement | 3000 random strings | DFA == regex for meter ID and reading |
| 05 | Messages | GRIDA123X / GRIDA12 / empty | Message names position, expected char, or "required" |
| 06 | Categories | TMP, OUT, OVR, HWF, COM | Five distinct categories |
| 07 | Conflict | OVR + "tampered ... display broken" | Tampering wins by priority rule, conflict noted |
| 08 | Invalid code | code ZZZ | No category, correction queue |
| 09 | No match | no code, vague text | No category, FALLBACK_UNCLASSIFIED |
| 10 | Unknown zone | GRIDZ123R | FALLBACK_UNKNOWN_ZONE, correction queue |
| 11 | Malformed ID | GRIDA12R | HTTP 422, stored as Rejected, not assigned |
| 12 | Dispatch | GRIDC123Y | Assigned to CREW-C, DIRECT |
| 13 | Capacity overflow | 7th report for section A | CREW-B, ESCALATED_BACKUP |
| 14 | Availability | CREW-C unavailable | CREW-B, ESCALATED_BACKUP |
| 15 | Waiting queue | all 30 slots full, then resolve one | Report waits, then auto-assigned |
| 16 | Priority override | Critical outage, all full | PRIORITY_OVERRIDE, crew shows 7 open |
| 17 | Queue ordering | Low, High, Medium waiting | High first, then Medium, then Low |
| 18 | Duplicates | dispatch called twice | One assignment, one open case |
| 19 | Status updates | skip / go back / repeat | Only Assigned > In Progress > Resolved allowed |
| 20 | Correction | fix category + section | Re-dispatched and assigned |
| 21 | End to end | submit, progress, resolve | Persisted in SQLite; dashboards update |
