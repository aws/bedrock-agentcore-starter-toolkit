"""Constants for observability operations."""

import os

# Default Time Ranges
DEFAULT_LOOKBACK_DAYS = int(os.getenv("AGENTCORE_DEFAULT_LOOKBACK_DAYS", "7"))


# Query Batch Sizes
DEFAULT_BATCH_SIZE = int(os.getenv("AGENTCORE_BATCH_SIZE", "50"))
