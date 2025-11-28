"""Builders for constructing telemetry models from CloudWatch Logs Insights results."""

import json
from typing import Any, Optional

from .telemetry import RuntimeLog, Span


class CloudWatchResultBuilder:
    """Builds telemetry models from CloudWatch Logs Insights query results."""

    @staticmethod
    def build_span(result: Any) -> Span:
        """Build a Span from CloudWatch Logs Insights query result.

        Args:
            result: List of field dictionaries from CloudWatch query result

        Returns:
            Span object populated from the result
        """
        fields = result if isinstance(result, list) else result.get("fields", [])

        def get_field(field_name: str, default: Any = None) -> Any:
            for field_item in fields:
                if field_item.get("field") == field_name:
                    return field_item.get("value", default)
            return default

        def parse_json_field(field_name: str) -> Any:
            """Parse JSON string field. CloudWatch returns @message as JSON string."""
            value = get_field(field_name)
            if value and isinstance(value, str):
                try:
                    return json.loads(value)
                except Exception:
                    return value
            return value

        def get_float(field_name: str) -> Optional[float]:
            """Get field as float. CloudWatch returns numeric fields as strings."""
            value = get_field(field_name)
            return float(value) if value is not None else None

        def get_int(field_name: str) -> Optional[int]:
            """Get field as int. CloudWatch returns numeric fields as strings."""
            value = get_field(field_name)
            return int(value) if value is not None else None

        # Parse @message to get attributes and resource.attributes
        raw_message = parse_json_field("@message")
        attributes = {}
        resource_attributes = {}

        if isinstance(raw_message, dict):
            attributes = raw_message.get("attributes", {}) or {}
            resource_data = raw_message.get("resource", {}) or {}
            resource_attributes = resource_data.get("attributes", {}) or {}

        return Span(
            trace_id=get_field("traceId", ""),
            span_id=get_field("spanId", ""),
            span_name=get_field("spanName", ""),
            session_id=get_field("sessionId"),
            start_time_unix_nano=get_int("startTimeUnixNano"),
            end_time_unix_nano=get_int("endTimeUnixNano"),
            duration_ms=get_float("durationMs"),
            status_code=get_field("statusCode"),
            status_message=get_field("statusMessage"),
            parent_span_id=get_field("parentSpanId"),
            kind=get_field("kind"),
            events=parse_json_field("events") or [],
            attributes=attributes,
            resource_attributes=resource_attributes,
            service_name=get_field("serviceName"),
            resource_id=get_field("resourceId"),
            service_type=get_field("serviceType"),
            timestamp=get_field("@timestamp"),
            raw_message=raw_message,
        )

    @staticmethod
    def build_runtime_log(result: Any) -> RuntimeLog:
        """Build a RuntimeLog from CloudWatch Logs Insights query result.

        Args:
            result: List of field dictionaries from CloudWatch query result

        Returns:
            RuntimeLog object populated from the result
        """
        fields = result if isinstance(result, list) else result.get("fields", [])

        def get_field(field_name: str, default: Any = None) -> Any:
            for field_item in fields:
                if field_item.get("field") == field_name:
                    return field_item.get("value", default)
            return default

        def parse_json_field(field_name: str) -> Any:
            """Parse JSON string field."""
            value = get_field(field_name)
            if value and isinstance(value, str):
                try:
                    return json.loads(value)
                except Exception:
                    return value
            return value

        return RuntimeLog(
            timestamp=get_field("@timestamp", ""),
            message=get_field("@message", ""),
            span_id=get_field("spanId"),
            trace_id=get_field("traceId"),
            log_stream=get_field("@logStream"),
            raw_message=parse_json_field("@message"),
        )
