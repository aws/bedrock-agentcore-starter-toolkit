# UX/DevEx Improvement Suggestions

## High Priority Improvements

### 1. Add List Evaluators Command

**Problem**: Users don't know what evaluators are available
**Solution**: Add `agentcore eval list-evaluators` command

```python
@evaluation_app.command("list-evaluators")
def list_evaluators():
    """List available evaluators and their descriptions."""
    table = Table(title="Available Evaluators", show_header=True)
    table.add_column("Evaluator", style="cyan")
    table.add_column("Scope", style="yellow")
    table.add_column("Description", style="dim")

    # Built-in evaluators (could fetch from control plane API later)
    evaluators = [
        ("Builtin.Helpfulness", "Trace", "Evaluates how helpful the response was"),
        ("Builtin.Accuracy", "Trace", "Evaluates factual accuracy of response"),
        ("Builtin.GoalSuccessRate", "Session", "Evaluates success rate across all traces"),
    ]

    for name, scope, desc in evaluators:
        table.add_row(name, scope, desc)

    console.print(table)
```

### 2. Add Progress Indicator for All Traces

**Problem**: `--all-traces` with many traces gives no feedback during execution
**Solution**: Show progress as traces are evaluated

```python
# In evaluate_all_traces loop:
for i, tid in enumerate(trace_ids, 1):
    console.print(f"\n[cyan]Evaluating trace {i}/{len(trace_ids)}:[/cyan] {tid}")
    # Show progress bar or spinner
```

### 3. Add Summary Statistics

**Problem**: No aggregate view of results
**Solution**: Show summary after evaluation

```python
def _display_summary_statistics(results: EvaluationResults):
    """Display aggregate statistics about evaluation results."""
    successful = results.get_successful_results()
    failed = results.get_failed_results()

    # Calculate statistics
    scores = [r.value for r in successful if r.value is not None]
    avg_score = sum(scores) / len(scores) if scores else 0

    # Display
    console.print("\n[bold cyan]Summary Statistics[/bold cyan]")
    console.print(f"  Total evaluations: {len(results.results)}")
    console.print(f"  Successful: [green]{len(successful)}[/green]")
    console.print(f"  Failed: [red]{len(failed)}[/red]")
    if scores:
        console.print(f"  Average score: [yellow]{avg_score:.2f}[/yellow]")
```

### 4. Add Output Format Options

**Problem**: Terminal output not machine-readable
**Solution**: Add `--format` option

```bash
# Human-readable (default)
agentcore eval run --session-id abc123

# JSON for piping to other tools
agentcore eval run --session-id abc123 --format json

# Compact for CI/CD
agentcore eval run --session-id abc123 --format compact
```

### 5. Improve Error Messages with Suggestions

**Problem**: Generic error messages don't guide users to solutions
**Solution**: Add context-aware suggestions

```python
except RuntimeError as e:
    if "No trace data found" in str(e):
        console.print(f"\n[red]Error:[/red] {e}")
        console.print("\n[yellow]Suggestions:[/yellow]")
        console.print("  • Check that the session ID is correct")
        console.print("  • Verify the session has completed and data is available")
        console.print("  • Try increasing the time range (wait a few minutes)")
        console.print("  • Run: agentcore obs query --session-id {session_id} to verify data")
    else:
        console.print(f"\n[red]Error:[/red] {e}")
```

### 6. Add Dry Run Mode

**Problem**: Users want to see what will be evaluated without running
**Solution**: Add `--dry-run` flag

```bash
agentcore eval run --session-id abc123 --dry-run

# Output:
# Would evaluate:
#   Session ID: abc123
#   Mode: Latest trace only
#   Evaluators: Builtin.Helpfulness
#   Estimated items to send: ~45 spans, ~20 log events
```

### 7. Add Verbose Mode for Debugging

**Problem**: Hard to debug issues without internal details
**Solution**: Add `--verbose` flag

```bash
agentcore eval run --session-id abc123 --verbose

# Shows:
# - Full API requests/responses
# - Detailed transformation steps
# - Timing information
# - Data filtering decisions
```

### 8. Better Status Messages

**Problem**: Generic "Running evaluation..." doesn't show progress
**Solution**: More specific status updates

```python
with console.status("[cyan]Fetching session data from CloudWatch...[/cyan]"):
    trace_data = obs_client.get_session_data(...)

with console.status("[cyan]Transforming to OpenTelemetry format...[/cyan]"):
    otel_spans = transform_trace_data_to_otel(...)

with console.status(f"[cyan]Evaluating with {len(evaluators)} evaluators...[/cyan]"):
    # Run evaluation
```

## Medium Priority Improvements

### 9. Add Evaluator Name Validation

**Problem**: Typos in evaluator names cause silent failures
**Solution**: Validate evaluator names early

```python
KNOWN_EVALUATORS = {
    "Builtin.Helpfulness",
    "Builtin.Accuracy",
    "Builtin.GoalSuccessRate",
}

def validate_evaluators(evaluators: List[str]):
    unknown = set(evaluators) - KNOWN_EVALUATORS
    if unknown:
        console.print(f"[yellow]Warning:[/yellow] Unknown evaluators: {', '.join(unknown)}")
        console.print("Run 'agentcore eval list-evaluators' to see available evaluators")
```

### 10. Cache Session Data for Multiple Evaluations

**Problem**: Re-fetching same session data for multiple evaluations
**Solution**: Cache data locally

```python
@lru_cache(maxsize=10)
def _fetch_session_data_cached(session_id, agent_id, region, start_time, end_time):
    # Fetch and cache for a few minutes
    pass
```

### 11. Add Watch Mode

**Problem**: Need to manually re-run evaluation for new traces
**Solution**: Add `--watch` flag

```bash
agentcore eval run --session-id abc123 --watch

# Continuously monitors for new traces and evaluates them
# Useful during development/testing
```

### 12. Add Comparison Mode

**Problem**: Hard to compare evaluations across sessions or over time
**Solution**: Add comparison commands

```bash
agentcore eval compare results1.json results2.json
agentcore eval diff --session-id abc123 --session-id def456
```

### 13. Add Interactive Mode

**Problem**: Users don't always know what options to use
**Solution**: Add interactive prompts

```bash
agentcore eval run --interactive

# Prompts:
# ? Enter session ID: abc123
# ? Evaluation mode: [Latest trace] / All traces / Specific trace
# ? Select evaluators: [x] Builtin.Helpfulness [ ] Builtin.Accuracy
# ? Export results? [y/N]
```

## Low Priority / Nice to Have

### 14. Add Evaluation Templates

```bash
agentcore eval run --template helpfulness-check
agentcore eval run --template full-quality-audit
```

### 15. Add Result Visualization

```bash
agentcore eval visualize results.json
# Opens browser with interactive charts
```

### 16. Add Batch Evaluation

```bash
agentcore eval batch --sessions sessions.txt --evaluator Builtin.Helpfulness
# Evaluates multiple sessions at once
```

### 17. Add Webhooks for Async Evaluation

```bash
agentcore eval run --session-id abc123 --webhook https://myapi.com/results
# Sends results to webhook when done (for CI/CD pipelines)
```

## CLI Help Improvements

### Current State:
```bash
agentcore eval run --help
# Shows basic options but no examples
```

### Improved State:
```bash
agentcore eval run --help

Usage: agentcore eval run [OPTIONS]

  Run evaluation on a session.

Options:
  --session-id TEXT         Session ID to evaluate
  --trace-id TEXT          Specific trace ID to evaluate
  --all-traces             Evaluate all traces in session
  -e, --evaluator TEXT     Evaluator(s) to use [default: Builtin.Helpfulness]
  -o, --output PATH        Save results to JSON file
  --format [table|json|compact]  Output format [default: table]
  --dry-run                Show what would be evaluated without running
  --verbose                Show detailed debug information
  --help                   Show this message and exit

Examples:
  # Evaluate latest trace with default evaluator
  agentcore eval run --session-id abc123

  # Evaluate specific trace
  agentcore eval run --session-id abc123 --trace-id xyz789

  # Evaluate all traces with multiple evaluators
  agentcore eval run --session-id abc123 --all-traces \\
    -e Builtin.Helpfulness \\
    -e Builtin.Accuracy

  # Export results and input data
  agentcore eval run --session-id abc123 -o results.json

  # Dry run to see what would be evaluated
  agentcore eval run --session-id abc123 --dry-run

For more information, visit:
  https://docs.example.com/evaluation
```

## Configuration Improvements

### Add Evaluation Presets in Config File

```yaml
# .bedrock_agentcore.yaml
evaluation:
  presets:
    quick-check:
      evaluators:
        - Builtin.Helpfulness
      mode: latest

    full-audit:
      evaluators:
        - Builtin.Helpfulness
        - Builtin.Accuracy
        - Builtin.GoalSuccessRate
      mode: all-traces

  defaults:
    evaluators:
      - Builtin.Helpfulness
    auto_export: true
    export_path: ./eval_results
```

Usage:
```bash
agentcore eval run --session-id abc123 --preset full-audit
```

## Error Handling Improvements

### Add Retry Logic with Exponential Backoff

```python
@retry(
    stop=stop_after_attempt(3),
    wait=wait_exponential(multiplier=1, min=2, max=10),
    retry=retry_if_exception_type(ClientError)
)
def evaluate(self, spans, evaluators):
    # API call with automatic retry
    pass
```

### Add Graceful Degradation

```python
# If one evaluator fails, continue with others
for evaluator in evaluators:
    try:
        result = self.evaluate(spans, [evaluator])
    except Exception as e:
        console.print(f"[yellow]Warning:[/yellow] {evaluator} failed, continuing...")
        # Add error result and continue
```

## Performance Improvements

### Add Parallel Evaluation for Multiple Traces

```python
from concurrent.futures import ThreadPoolExecutor, as_completed

# Evaluate traces in parallel
with ThreadPoolExecutor(max_workers=5) as executor:
    futures = {
        executor.submit(self.evaluate, otel_spans, evaluators): tid
        for tid, otel_spans in trace_data.items()
    }

    for future in as_completed(futures):
        tid = futures[future]
        try:
            result = future.result()
        except Exception as e:
            # Handle error
```

### Add Request Batching

```python
# Instead of one API call per evaluator, batch multiple evaluators
response = self.evaluate(spans, evaluators=["Builtin.Helpfulness", "Builtin.Accuracy"])
```
