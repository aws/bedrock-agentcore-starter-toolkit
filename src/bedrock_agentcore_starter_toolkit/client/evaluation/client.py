"""User-friendly Evaluation client for Python scripts and notebooks."""

import json
from pathlib import Path
from typing import List, Optional

from rich.console import Console
from rich.panel import Panel
from rich.text import Text

from ...operations.evaluation.client import EvaluationClient
from ...operations.evaluation.models.evaluation import EvaluationResults

console = Console()


class Evaluation:
    """Simple interface for evaluating agent sessions.

    Example:
        # Initialize with agent info
        eval_client = Evaluation(agent_id="my-agent", region="us-east-1")

        # Evaluate a session
        results = eval_client.evaluate("session-123")

        # Display results
        eval_client.display(results)

        # Or from config file
        eval_client = Evaluation.from_config()
        results = eval_client.evaluate()  # Uses session from config
    """

    def __init__(
        self,
        agent_id: Optional[str] = None,
        region: Optional[str] = None,
        session_id: Optional[str] = None,
        endpoint_url: Optional[str] = None,
    ):
        """Initialize Evaluation client.

        Args:
            agent_id: Agent ID to evaluate (required if not using from_config)
            region: AWS region (required if not using from_config)
            session_id: Optional default session ID for convenience
            endpoint_url: Optional custom evaluation API endpoint
        """
        self.agent_id = agent_id
        self.region = region
        self.session_id = session_id

        # Initialize evaluation client
        self._client = EvaluationClient(region=region, endpoint_url=endpoint_url)

    @classmethod
    def from_config(cls, config_path: Optional[Path] = None, agent_name: Optional[str] = None) -> "Evaluation":
        """Create Evaluation client from config file.

        Args:
            config_path: Path to config file (default: .bedrock_agentcore.yaml in cwd)
            agent_name: Agent name from config (uses first agent if not specified)

        Returns:
            Configured Evaluation instance

        Example:
            eval_client = Evaluation.from_config()
            results = eval_client.evaluate()
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
            session_id=agent_config.bedrock_agentcore.agent_session_id,
        )

    def evaluate(
        self,
        session_id: Optional[str] = None,
        evaluators: Optional[List[str]] = None,
        trace_id: Optional[str] = None,
        all_traces: bool = False,
    ) -> EvaluationResults:
        """Evaluate a session with one or more evaluators.

        Args:
            session_id: Session ID to evaluate (uses default if not provided)
            evaluators: List of evaluators to use (default: ["Builtin.Helpfulness"])
            trace_id: Optional specific trace ID to evaluate
            all_traces: Evaluate all traces in session (default: False, evaluates latest)

        Returns:
            EvaluationResults with scores and explanations

        Example:
            # Evaluate with default evaluator
            results = eval_client.evaluate("session-123")

            # Evaluate with multiple evaluators
            results = eval_client.evaluate(
                "session-123",
                evaluators=["Builtin.Helpfulness", "Builtin.Accuracy"]
            )

            # Evaluate all traces
            results = eval_client.evaluate("session-123", all_traces=True)
        """
        session_id = session_id or self.session_id
        if not session_id:
            raise ValueError("No session_id provided")

        if not self.agent_id or not self.region:
            raise ValueError("Agent ID and region required. Provide them in __init__ or use from_config()")

        evaluators = evaluators or ["Builtin.Helpfulness"]

        return self._client.evaluate_session(
            session_id=session_id,
            evaluators=evaluators,
            agent_id=self.agent_id,
            region=self.region,
            trace_id=trace_id,
            all_traces=all_traces,
        )

    def display(self, results: EvaluationResults) -> None:
        """Display evaluation results in a formatted way.

        Args:
            results: EvaluationResults to display

        Example:
            results = eval_client.evaluate("session-123")
            eval_client.display(results)
        """
        # Header
        header = Text()
        header.append("Evaluation Results\n", style="bold cyan")
        if results.session_id:
            header.append(f"Session: {results.session_id}\n", style="dim")
        if results.trace_id:
            header.append(f"Trace: {results.trace_id}\n", style="dim")

        console.print(Panel(header, border_style="cyan"))

        # Display successful results
        successful = results.get_successful_results()
        if successful:
            console.print("\n[bold green]✓ Successful Evaluations[/bold green]\n")

            for result in successful:
                content = Text()

                # Evaluator name
                content.append("Evaluator: ", style="bold")
                content.append(f"{result.evaluator}\n\n", style="cyan")

                # Score/Label
                if result.value is not None:
                    content.append("Score: ", style="bold")
                    content.append(f"{result.value:.2f}\n", style="green")

                if result.label:
                    content.append("Label: ", style="bold")
                    content.append(f"{result.label}\n", style="green")

                # Explanation
                if result.explanation:
                    content.append("\nExplanation:\n", style="bold")
                    content.append(f"{result.explanation}\n")

                # Token usage
                if result.token_usage:
                    content.append("\nToken Usage:\n", style="bold")
                    content.append(f"  - Input: {result.token_usage.get('inputTokens', 0):,}\n", style="dim")
                    content.append(f"  - Output: {result.token_usage.get('outputTokens', 0):,}\n", style="dim")
                    content.append(f"  - Total: {result.token_usage.get('totalTokens', 0):,}\n", style="dim")

                console.print(Panel(content, border_style="green", padding=(1, 2)))

        # Display failed results
        failed = results.get_failed_results()
        if failed:
            console.print("\n[bold red]✗ Failed Evaluations[/bold red]\n")

            for result in failed:
                content = Text()
                content.append("Evaluator: ", style="bold")
                content.append(f"{result.evaluator}\n\n", style="cyan")
                content.append("Error: ", style="bold red")
                content.append(f"{result.error}\n", style="red")

                console.print(Panel(content, border_style="red", padding=(1, 2)))

    def save(self, results: EvaluationResults, output_file: str) -> None:
        """Save evaluation results to a JSON file.

        Args:
            results: EvaluationResults to save
            output_file: Path to output file

        Example:
            results = eval_client.evaluate("session-123")
            eval_client.save(results, "results.json")
        """
        output_path = Path(output_file)
        output_path.parent.mkdir(parents=True, exist_ok=True)

        # Save results
        results_dict = results.to_dict()
        input_data = results_dict.pop("input_data", None)

        with open(output_path, "w") as f:
            json.dump(results_dict, f, indent=2, default=str)

        console.print(f"\n[green]✓[/green] Results saved to: {output_path}")

        # Save input data to separate file if present
        if input_data is not None:
            stem = output_path.stem
            suffix = output_path.suffix
            input_path = output_path.parent / f"{stem}_input{suffix}"

            with open(input_path, "w") as f:
                json.dump(input_data, f, indent=2, default=str)

            console.print(f"[green]✓[/green] Input data saved to: {input_path}")
