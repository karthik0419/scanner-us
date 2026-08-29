# ==============================
# DATA SETTINGS
# ==============================

DATA_PERIOD = "12mo"
DATA_INTERVAL = "1d"


# ==============================
# PATTERN SETTINGS
# ==============================

LOOKBACK_PERIOD = 50

# Breakout detection
RESISTANCE_THRESHOLD = 0.93   # near breakout (93% of resistance)
BREAKOUT_BUFFER = 0.995       # breakout trigger buffer

# Volume
VOLUME_LOOKBACK = 20
VOLUME_MULTIPLIER = 1.5


# ==============================
# RISK MANAGEMENT
# ==============================

STOP_LOSS_BUFFER = 0.97   # 3% below breakout


# ==============================
# SCORING SETTINGS
# ==============================

RR_HIGH = 2.0
RR_MEDIUM = 1.5

NEAR_BREAKOUT_THRESHOLD = 0.03


# ==============================
# FILTERS
# ==============================

MIN_CANDLES = 140