"""User-friendly Observability client for Python scripts and notebooks."""

from datetime import datetime, timedelta
from pathlib import Path
from typing import Optional

from ...operations.observability.client import ObservabilityClient
from ...operations.observability.models.telemetry import TraceData
from ...operations.observability.visualizers.trace_visualizer import TraceVisualizer


class Observability:
    """Simple interface for querying and visualizing agent traces.

    Example:
        # Initialize with agent ID
        obs = Observability(agent_id="my-agent-id", region="us-east-1")

        # Get traces for a session
        traces = obs.get_session("session-123")

        # Visualize traces
        obs.visualize(traces)

        # Or from config file
        obs = Observability.from_config()
        traces = obs.get_latest_session()
        obs.visualize(traces)
    """

    def __init__(
        self,
        agent_id: Optional[str] = None,
        region: Optional[str] = None,
        runtime_suffix: str = "DEFAULT",
        session_id: Optional[str] = None,
    ):
        """Initialize Observability client.

        Args:
            agent_id: Agent ID to query (required if not using from_config)
            region: AWS region (required if not using from_config)
            runtime_suffix: Runtime suffix (default: "DEFAULT")
            session_id: Optional default session ID for convenience
        """
        self.agent_id = agent_id
        self.region = region
        self.runtime_suffix = runtime_suffix
        self.session_id = session_id

        # Initialize client if we have required params
        self._client = None
        if agent_id and region:
            self._client = ObservabilityClient(region_name=region, agent_id=agent_id, runtime_suffix=runtime_suffix)

        self._visualizer = TraceVisualizer()

    @classmethod
    def from_config(cls, config_path: Optional[Path] = None, agent_name: Optional[str] = None) -> "Observability":
        """Create Observability client from config file.

        Args:
            config_path: Path to config file (default: .bedrock_agentcore.yaml in cwd)
            agent_name: Agent name from config (uses first agent if not specified)

        Returns:
            Configured Observability instance

        Example:
            obs = Observability.from_config()
            traces = obs.get_latest_session()
        """
        # Import here to avoid circular dependency
        from ...utils.runtime.config import load_config_if_exists

        if config_path is None:
            config_path = Path.cwd() / ".bedrock_agentcore.yaml"

        config = load_config_if_exists(config_path)
        if not config:
            raise ValueError(f"No config file found at {config_path}")

        agent_config = config.get_agent_config(agent_name)

        return cls(
            agent_id=agent_config.bedrock_agentcore.agent_id,
            region=agent_config.aws.region,
            runtime_suffix="DEFAULT",
            session_id=agent_config.bedrock_agentcore.agent_session_id,
        )

    def _ensure_client(self):
        """Ensure client is initialized."""
        if not self._client:
            raise ValueError("Observability client not initialized. Provide agent_id and region, or use from_config()")

    def get_session(
        self, session_id: Optional[str] = None, lookback_days: int = 7, include_runtime_logs: bool = True
    ) -> TraceData:
        """Get all traces and logs for a session.

        Args:
            session_id: Session ID to query (uses default if not provided)
            lookback_days: How many days back to search (default: 7)
            include_runtime_logs: Include runtime logs (default: True)

        Returns:
            TraceData with spans and logs

        Example:
            traces = obs.get_session("session-123")
            print(f"Found {len(traces.spans)} spans")
        """
        self._ensure_client()

        session_id = session_id or self.session_id
        if not session_id:
            raise ValueError("No session_id provided")

        # Calculate time range
        end_time = datetime.now()
        start_time = end_time - timedelta(days=lookback_days)
        start_time_ms = int(start_time.timestamp() * 1000)
        end_time_ms = int(end_time.timestamp() * 1000)

        return self._client.get_session_data(
            session_id=session_id,
            start_time_ms=start_time_ms,
            end_time_ms=end_time_ms,
            include_runtime_logs=include_runtime_logs,
        )

    def get_latest_session(self, lookback_days: int = 1, include_runtime_logs: bool = True) -> Optional[TraceData]:
        """Get the most recent session.

        Args:
            lookback_days: How many days back to search (default: 1)
            include_runtime_logs: Include runtime logs (default: True)

        Returns:
            TraceData for latest session or None if no sessions found

        Example:
            traces = obs.get_latest_session()
            if traces:
                obs.visualize(traces)
        """
        self._ensure_client()

        # Calculate time range
        end_time = datetime.now()
        start_time = end_time - timedelta(days=lookback_days)
        start_time_ms = int(start_time.timestamp() * 1000)
        end_time_ms = int(end_time.timestamp() * 1000)

        # Query for recent sessions
        sessions = self._client.query_recent_sessions(start_time_ms=start_time_ms, end_time_ms=end_time_ms, limit=1)

        if not sessions:
            return None

        # Get full trace data for the latest session
        latest_session_id = sessions[0].session_id
        return self.get_session(
            session_id=latest_session_id, lookback_days=lookback_days, include_runtime_logs=include_runtime_logs
        )

    def visualize(
        self,
        trace_data: TraceData,
        output_format: str = "tree",
        truncate_at: int = 250,
        show_timing: bool = True,
        show_attributes: bool = False,
    ) -> None:
        """Visualize trace data in the console.

        Args:
            trace_data: TraceData to visualize
            output_format: Format to use ("tree" or "table")
            truncate_at: Truncate long content at N characters (default: 250)
            show_timing: Show timing information (default: True)
            show_attributes: Show span attributes (default: False)

        Example:
            traces = obs.get_session("session-123")
            obs.visualize(traces, output_format="tree")
        """
        if output_format == "tree":
            self._visualizer.display_trace_tree(
                trace_data, truncate_at=truncate_at, show_timing=show_timing, show_attributes=show_attributes
            )
        elif output_format == "table":
            self._visualizer.display_trace_table(trace_data)
        else:
            raise ValueError(f"Unknown format: {output_format}. Use 'tree' or 'table'")
