"""Central configuration: routing table, capacities, enums."""

CREW_CAPACITY = 6                      # max open cases (Assigned + In Progress) per crew
PHASES = "RYB"                         # valid PHASE letters in the meter ID
URGENCIES = ["Low", "Medium", "High", "Critical"]
STATUSES = ["Pending", "Assigned", "In Progress", "Resolved"]
NEXT_STATUS = {"Assigned": "In Progress", "In Progress": "Resolved"}
CATEGORIES = ["Tampering", "Outage", "Overconsumption", "Hardware", "Communication"]

# Explicit routing / dispatch table. Key = section letter taken from the meter ID
# (GRID<letter><3 digits><phase>). Section order also defines "nearest" crew.
SECTIONS = {
    "A": {"crew": "CREW-A", "name": "Crew Alpha",   "zone": "North Grid",   "depot": "Depot North"},
    "B": {"crew": "CREW-B", "name": "Crew Bravo",   "zone": "East Grid",    "depot": "Depot East"},
    "C": {"crew": "CREW-C", "name": "Crew Charlie", "zone": "Central Grid", "depot": "Depot Central"},
    "D": {"crew": "CREW-D", "name": "Crew Delta",   "zone": "South Grid",   "depot": "Depot South"},
    "E": {"crew": "CREW-E", "name": "Crew Echo",    "zone": "West Grid",    "depot": "Depot West"},
}

QUEUE_WAITING = "WAITING"              # valid report, every eligible crew full/unavailable
QUEUE_CORRECTION = "CORRECTION"        # central fallback: unknown zone / unclassified
