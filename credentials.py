"""Demo access credentials and key-cycle configuration."""

# 1-minute rotating trial keys (10 keys).
ONE_MIN_TRIAL_KEYS = [
    "TRL-7K2P-X9W1-B4R8",
    "TRL-3M9V-L2N6-Q8Z5",
    "TRL-5H1B-D7S4-K9W2",
    "TRL-8X4J-C2M9-P1V6",
    "TRL-2N6Y-G8H3-F5S1",
    "TRL-9B1K-R4W7-D2M5",
    "TRL-4S8V-Z9P1-Q3L6",
    "TRL-6J2C-H5N8-X7W4",
    "TRL-1M9G-K3R6-B2D8",
    "TRL-7V4S-L8N2-P5Q9",
]

# 3-minute rotating trial keys (10 keys).
THREE_MIN_TRIAL_KEYS = [
    "TR3-8P1K-M7V4-D2R9",
    "TR3-4N6B-Q2W8-L9S1",
    "TR3-9H3C-X5M1-P7V6",
    "TR3-2J8R-D4K9-B1N5",
    "TR3-6S5V-Z1P2-Q8L4",
    "TR3-1M7G-K9R3-D6B2",
    "TR3-5X2W-H8N4-C1J9",
    "TR3-7B9L-P3S6-V4K1",
    "TR3-3Q4D-N1M8-R5X7",
    "TR3-8V6C-L2H5-W9P3",
]

# 5-minute rotating trial keys (10 keys).
FIVE_MIN_TRIAL_KEYS = [
    "TR5-9K2M-R7V1-B4P8",
    "TR5-3D8Q-L1N6-X5S2",
    "TR5-6H4B-P9W3-C2R7",
    "TR5-1J7V-K5M2-D8L4",
    "TR5-8N3S-Z6P1-Q4X9",
    "TR5-2M9G-B4R8-L1D6",
    "TR5-7X1C-H3N5-V8W2",
    "TR5-4P6L-K2S9-R3B1",
    "TR5-5Q8D-N7M4-J1X6",
    "TR5-9V2C-L8H1-W6P4",
]

# Ordered key groups used by the app. Each group cycles independently.
TRIAL_KEY_GROUPS = [
    {"id": "trial_1m", "duration_sec": 60, "keys": ONE_MIN_TRIAL_KEYS},
    {"id": "trial_3m", "duration_sec": 180, "keys": THREE_MIN_TRIAL_KEYS},
    {"id": "trial_5m", "duration_sec": 300, "keys": FIVE_MIN_TRIAL_KEYS},
]

# Unlimited admin key.
ADMIN_KEY = "ADM-X92F-88B1-CC40-19E2-7D6A-BK99"

# Backward-compat aliases (optional).
TRIAL_KEYS = ONE_MIN_TRIAL_KEYS
TRIAL_DURATION_SEC = 60
