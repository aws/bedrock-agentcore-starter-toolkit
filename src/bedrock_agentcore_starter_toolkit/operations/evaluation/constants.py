"""Constants for evaluation operations."""

import os

# API Configuration
DEFAULT_MAX_EVALUATION_ITEMS = int(os.getenv("AGENTCORE_MAX_EVAL_ITEMS", "1000"))
MAX_SPAN_IDS_IN_CONTEXT = int(os.getenv("AGENTCORE_MAX_SPAN_IDS", "20"))


# Session-Scoped Evaluators
# These evaluators require data across all traces in a session
SESSION_SCOPED_EVALUATORS = {
    "Builtin.GoalSuccessRate",
}
