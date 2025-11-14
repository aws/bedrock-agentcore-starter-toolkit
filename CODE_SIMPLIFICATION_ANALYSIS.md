# Code Simplification & Generalization Analysis

## Executive Summary

This document identifies hardcoded values, repeated patterns, and opportunities for simplification across the observability and evaluation codebase.

## 1. Hardcoded Constants

### 1.1 Evaluation Client (`evaluation/client.py`)

**Issue: Magic Number for Max Items**
```python
# Line 100, 242, 514: Hardcoded 100 for max items
max_items=100
```

**Recommendation:**
```python
# evaluation/constants.py
DEFAULT_MAX_EVALUATION_ITEMS = 100
MAX_SPAN_IDS_IN_CONTEXT = 20  # Line 174

# Use environment variable override
MAX_EVALUATION_ITEMS = int(os.getenv("AGENTCORE_MAX_EVAL_ITEMS", "100"))
```

**Impact:** High - Affects API payload size and cost

---

### 1.2 Trace Visualizer (`visualizers/trace_visualizer.py`)

**Issue: Multiple Hardcoded Truncation Limits**
```python
# Line 250, 292, 299, 307, 316, 322: Hardcoded 250 character limit
if not verbose and len(content) > 250:
    content = content[:250] + "..."

# Line 369: Special case 150
content = first_line[:150] + "... [truncated tool use]"

# Line 482, 496, 507: Same 250 limit in payload display
if not verbose and len(value_str) > 250:
    value_str = value_str[:250] + "..."
```

**Recommendation:**
```python
# visualizers/constants.py
DEFAULT_CONTENT_TRUNCATION_LENGTH = 250
TOOL_USE_TRUNCATION_LENGTH = 150
TRUNCATION_MARKER = "..."

class TruncationConfig:
    def __init__(self, length: int = 250, tool_use_length: int = 150):
        self.content_length = length
        self.tool_use_length = tool_use_length
        self.marker = "..."

    def truncate(self, text: str, is_tool_use: bool = False) -> str:
        max_len = self.tool_use_length if is_tool_use else self.content_length
        if len(text) > max_len:
            return text[:max_len] + self.marker
        return text
```

**Impact:** Medium - Affects readability and user experience

---

### 1.3 Observability Commands (`cli/observability/commands.py`)

**Issue: Hardcoded Time Range**
```python
# Line 111: Hardcoded 7 days default
days: int = typer.Option(7, "--days", "-d", help="Number of days to look back")
```

**Recommendation:**
```python
# cli/constants.py
DEFAULT_LOOKBACK_DAYS = int(os.getenv("AGENTCORE_DEFAULT_LOOKBACK_DAYS", "7"))

# Allow configuration via environment or config file
days: int = typer.Option(
    DEFAULT_LOOKBACK_DAYS,
    "--days", "-d",
    help=f"Number of days to look back (default: {DEFAULT_LOOKBACK_DAYS})"
)
```

**Impact:** Low - User can already override via CLI

---

### 1.4 Runtime Suffix (`operations/observability/client.py`)

**Issue: Hardcoded "DEFAULT" Runtime Suffix**
```python
# Multiple locations: Lines 69, 75
runtime_suffix="DEFAULT"
```

**Recommendation:**
```python
# observability/constants.py
DEFAULT_RUNTIME_SUFFIX = os.getenv("AGENTCORE_RUNTIME_SUFFIX", "DEFAULT")

class ObservabilityClient:
    def __init__(
        self,
        region_name: str,
        agent_id: str,
        runtime_suffix: str = DEFAULT_RUNTIME_SUFFIX
    ):
        ...
```

**Impact:** Low - Already parameterized in most places

---

## 2. Repeated String Literals

### 2.1 Gen AI Attribute Prefix

**Issue: "gen_ai" scattered throughout codebase**

**Locations:**
- `evaluation/client.py`: Lines 253, 301, 359, 483, 527
- `visualizers/trace_visualizer.py`: Lines 174-178, 289, 296
- `telemetry.py`: Lines 166, 200+

**Current:**
```python
if any(k.startswith('gen_ai') for k in span.get('attributes', {}).keys())
span.attributes.get("gen_ai.prompt")
if event_name.startswith("gen_ai."):
```

**Recommendation:**
```python
# observability/constants.py
class AttributePrefixes:
    GEN_AI = "gen_ai"
    LLM = "llm"
    EXCEPTION = "exception"
    EVENT = "event"
    SESSION = "session"
    TRACE = "trace"

class GenAIAttributes:
    PROMPT = f"{AttributePrefixes.GEN_AI}.prompt"
    COMPLETION = f"{AttributePrefixes.GEN_AI}.completion"
    USER_MESSAGE = f"{AttributePrefixes.GEN_AI}.user.message"
    ASSISTANT_MESSAGE = f"{AttributePrefixes.GEN_AI}.assistant.message"
    TOOL_MESSAGE = f"{AttributePrefixes.GEN_AI}.tool.message"
    CHOICE = f"{AttributePrefixes.GEN_AI}.choice"

# Usage
def has_gen_ai_attrs(span: Dict) -> bool:
    return any(
        k.startswith(AttributePrefixes.GEN_AI)
        for k in span.get('attributes', {}).keys()
    )
```

**Impact:** High - Reduces typos, improves maintainability

---

### 2.2 Field Names

**Issue: Repeated field name strings**

**Current:**
```python
# Scattered throughout
"spanId", "traceId", "sessionId", "startTimeUnixNano", "endTimeUnixNano"
item.get("spanId")
span.get("traceId")
```

**Recommendation:**
```python
# models/constants.py
class OTelFields:
    SPAN_ID = "spanId"
    TRACE_ID = "traceId"
    SESSION_ID = "sessionId"
    START_TIME = "startTimeUnixNano"
    END_TIME = "endTimeUnixNano"
    ATTRIBUTES = "attributes"
    BODY = "body"
    TIME_UNIX_NANO = "timeUnixNano"

# Usage
span.get(OTelFields.SPAN_ID)
item[OTelFields.TRACE_ID]
```

**Impact:** Medium - Reduces typos, improves refactoring

---

## 3. Duplicated Logic

### 3.1 Span Filtering Logic

**Issue: Filter logic duplicated in multiple places**

**Locations:**
- `evaluation/client.py`: `_filter_relevant_items()` (Lines 89-125)
- Similar patterns in transformer and other places

**Current:** 50+ lines of filtering logic with inline attribute checks

**Recommendation:**
```python
# models/filters.py
class SpanFilter:
    """Configurable span filter with multiple criteria."""

    def __init__(
        self,
        require_gen_ai_attrs: bool = True,
        allowed_event_prefixes: List[str] = None,
        min_duration_ms: Optional[float] = None
    ):
        self.require_gen_ai_attrs = require_gen_ai_attrs
        self.allowed_event_prefixes = allowed_event_prefixes or [AttributePrefixes.GEN_AI]
        self.min_duration_ms = min_duration_ms

    def is_span(self, item: Dict) -> bool:
        return OTelFields.SPAN_ID in item and OTelFields.START_TIME in item

    def is_log(self, item: Dict) -> bool:
        return OTelFields.BODY in item and OTelFields.TIME_UNIX_NANO in item

    def has_gen_ai_attributes(self, span: Dict) -> bool:
        attrs = span.get(OTelFields.ATTRIBUTES, {})
        return any(k.startswith(AttributePrefixes.GEN_AI) for k in attrs.keys())

    def is_conversation_log(self, log: Dict) -> bool:
        body = log.get(OTelFields.BODY, {})
        if isinstance(body, dict):
            attrs = body.get(OTelFields.ATTRIBUTES, {})
            event_name = attrs.get("event.name", "")
            return any(event_name.startswith(prefix) for prefix in self.allowed_event_prefixes)
        return False

    def matches(self, item: Dict) -> bool:
        """Check if item matches filter criteria."""
        if self.is_span(item):
            return not self.require_gen_ai_attrs or self.has_gen_ai_attributes(item)
        elif self.is_log(item):
            return self.is_conversation_log(item)
        return False

    def filter(self, items: List[Dict]) -> List[Dict]:
        """Filter a list of items."""
        return [item for item in items if self.matches(item)]

# Usage
filter = SpanFilter(require_gen_ai_attrs=True)
filtered_spans = filter.filter(all_spans)
```

**Impact:** High - Simplifies 3-4 different implementations

---

### 3.2 Time Calculation Logic

**Issue: Time conversion logic repeated**

**Locations:**
- `commands.py`: Lines 512, 533, 545-553 (age calculation)
- `telemetry.py`: Lines 807-816 (duration calculation)
- `visualizer.py`: Lines 116 (duration calculation)

**Recommendation:**
```python
# utils/time_utils.py
from datetime import datetime, timedelta
from typing import Optional

def nanos_to_millis(nanos: int) -> float:
    """Convert nanoseconds to milliseconds."""
    return nanos / 1_000_000

def millis_to_nanos(millis: float) -> int:
    """Convert milliseconds to nanoseconds."""
    return int(millis * 1_000_000)

def format_age(timestamp_nanos: int) -> str:
    """Format timestamp as human-readable age (e.g., '5m ago', '2h ago')."""
    now_nanos = datetime.now().timestamp() * 1_000_000_000
    age_seconds = (now_nanos - timestamp_nanos) / 1_000_000_000

    if age_seconds < 60:
        return f"{int(age_seconds)}s ago"
    elif age_seconds < 3600:
        return f"{int(age_seconds / 60)}m ago"
    elif age_seconds < 86400:
        return f"{int(age_seconds / 3600)}h ago"
    else:
        return f"{int(age_seconds / 86400)}d ago"

def calculate_duration(
    start_time_nanos: Optional[int],
    end_time_nanos: Optional[int]
) -> Optional[float]:
    """Calculate duration in milliseconds from start/end timestamps."""
    if start_time_nanos and end_time_nanos:
        return (end_time_nanos - start_time_nanos) / 1_000_000
    return None
```

**Impact:** Medium - Reduces duplication, improves testability

---

## 4. Role Discovery Complexity

### 4.1 RuntimeLog Role Discovery

**Issue: 130+ lines of complex role/content discovery logic**

**Location:** `telemetry.py` lines 189-333

**Current:** Multiple nested methods with repeated patterns

**Recommendation:**
```python
# models/message_extractors.py
class MessageExtractor:
    """Base class for extracting messages from runtime logs."""

    def extract(self, log: RuntimeLog) -> Optional[Dict[str, Any]]:
        raise NotImplementedError

class RoleExtractor:
    """Extract role from various log formats."""

    def __init__(self):
        self.extractors = [
            StructuralRoleExtractor(),
            EventNameRoleExtractor(),
            BodyRoleExtractor(),
            LegacyRoleExtractor()
        ]

    def extract(self, event_name: str, body: Dict) -> Optional[str]:
        for extractor in self.extractors:
            role = extractor.extract(event_name, body)
            if role:
                return role
        return None

class ContentExtractor:
    """Extract content from various log formats."""

    def __init__(self):
        self.extractors = [
            StringBodyExtractor(),
            NestedMessageExtractor(),
            DirectContentExtractor(),
            LegacyContentExtractor()
        ]

    def extract(self, body: Any, role: str) -> Optional[str]:
        for extractor in self.extractors:
            content = extractor.extract(body, role)
            if content:
                return content
        return None

# Each extractor is simple and testable
class EventNameRoleExtractor:
    def extract(self, event_name: str, body: Dict) -> Optional[str]:
        # gen_ai.user.message -> user
        if "." in event_name:
            parts = event_name.split(".")
            if len(parts) >= 3 and parts[2] == "message":
                return parts[1]
        return None
```

**Impact:** Very High - Simplifies complex logic, improves testability

---

## 5. Configuration Centralization

### 5.1 Scattered Configuration

**Issue:** Configuration values scattered across multiple files

**Recommendation:** Create centralized configuration module

```python
# config/__init__.py
from dataclasses import dataclass
import os

@dataclass
class EvaluationConfig:
    """Configuration for evaluation operations."""
    max_items: int = int(os.getenv("AGENTCORE_MAX_EVAL_ITEMS", "100"))
    max_span_ids_in_context: int = int(os.getenv("AGENTCORE_MAX_SPAN_IDS", "20"))
    timeout_seconds: int = int(os.getenv("AGENTCORE_EVAL_TIMEOUT", "120"))

@dataclass
class ObservabilityConfig:
    """Configuration for observability operations."""
    default_lookback_days: int = int(os.getenv("AGENTCORE_LOOKBACK_DAYS", "7"))
    runtime_suffix: str = os.getenv("AGENTCORE_RUNTIME_SUFFIX", "DEFAULT")
    batch_size: int = int(os.getenv("AGENTCORE_BATCH_SIZE", "50"))

@dataclass
class VisualizationConfig:
    """Configuration for visualization display."""
    content_truncation_length: int = int(os.getenv("AGENTCORE_TRUNCATE_AT", "250"))
    tool_use_truncation_length: int = int(os.getenv("AGENTCORE_TOOL_TRUNCATE_AT", "150"))
    show_span_ids_count: int = 3
    truncation_marker: str = "..."

@dataclass
class AppConfig:
    """Master configuration."""
    evaluation: EvaluationConfig = EvaluationConfig()
    observability: ObservabilityConfig = ObservabilityConfig()
    visualization: VisualizationConfig = VisualizationConfig()

# Global config instance
config = AppConfig()
```

**Impact:** Very High - Single source of truth for all configuration

---

## 6. Error Message Standardization

### 6.1 Inconsistent Error Messages

**Issue:** Error messages use different formats

**Current:**
```python
# Different styles across codebase
print(f"[red]Error:[/red] {str(e)}")
console.print("[red]Error:[/red] Missing required parameters")
raise RuntimeError("Failed to transform trace data")
logger.error("Query failed: %s", e)
```

**Recommendation:**
```python
# utils/errors.py
class ObservabilityError(Exception):
    """Base exception for observability operations."""
    pass

class EvaluationError(Exception):
    """Base exception for evaluation operations."""
    pass

class ErrorMessages:
    """Standardized error messages."""

    MISSING_PARAMS = "Missing required parameters: {params}"
    TRANSFORM_FAILED = "Failed to transform {data_type}: {reason}"
    API_ERROR = "API error ({code}): {message}"
    NO_DATA_FOUND = "No {data_type} found for {identifier}"

    @staticmethod
    def format(template: str, **kwargs) -> str:
        return template.format(**kwargs)

# Usage
if not agent_id:
    raise ObservabilityError(
        ErrorMessages.format(
            ErrorMessages.MISSING_PARAMS,
            params="agent_id, region"
        )
    )
```

**Impact:** Medium - Improves consistency and i18n readiness

---

## 7. Recommended Implementation Priority

### Phase 1: High Impact, Low Risk
1. **Create constants module** (1 day)
   - Define all string literals as constants
   - Define magic numbers as named constants

2. **Centralize configuration** (2 days)
   - Create AppConfig with env var support
   - Update all modules to use config

### Phase 2: Medium Impact, Medium Risk
3. **Extract SpanFilter** (2 days)
   - Create reusable filter class
   - Replace all inline filtering

4. **Create time utils** (1 day)
   - Centralize time conversion logic
   - Add comprehensive tests

### Phase 3: High Impact, Higher Risk
5. **Refactor role/content discovery** (3-4 days)
   - Create extractor pattern
   - Extract individual extractors
   - Comprehensive testing required

6. **Create truncation helper** (1 day)
   - Single class for all truncation
   - Configurable limits

### Phase 4: Polish
7. **Standardize error messages** (1 day)
8. **Add configuration documentation** (1 day)
9. **Update tests** (2 days)

---

## 8. Backwards Compatibility

All changes should maintain backwards compatibility:
- Use environment variables for configuration overrides
- Keep existing function signatures (add defaults)
- Deprecate old patterns gradually

---

## 9. Testing Strategy

For each refactoring:
1. Add unit tests for new utilities
2. Keep integration tests passing
3. Add configuration tests
4. Document migration path

---

## 10. Benefits Summary

### Immediate Benefits
- **Maintainability**: Single source of truth for constants
- **Flexibility**: Environment variable configuration
- **Testability**: Smaller, focused functions
- **Consistency**: Standardized patterns

### Long-term Benefits
- **Extensibility**: Easy to add new extractors/filters
- **Performance**: Opportunity for caching/optimization
- **Documentation**: Clear configuration options
- **Debugging**: Easier to trace issues

---

## Conclusion

The codebase has grown organically with good functionality but would benefit from:
1. **Constants extraction** - Eliminate magic numbers and strings
2. **Configuration centralization** - Single config source
3. **Logic extraction** - Reusable filter/extractor classes
4. **Standardization** - Consistent error handling and patterns

Recommended approach: **Incremental refactoring** over 2-3 sprint cycles, maintaining backwards compatibility throughout.
