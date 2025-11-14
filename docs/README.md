# Bedrock AgentCore Starter Toolkit Documentation

Welcome to the Bedrock AgentCore Starter Toolkit documentation!

## Overview

The Bedrock AgentCore Starter Toolkit provides comprehensive observability and evaluation capabilities for your Bedrock AgentCore agents. Monitor execution, analyze performance, and evaluate quality with powerful CLI tools and Python APIs.

### Key Features

✅ **Observability**
- Query traces and spans from CloudWatch Logs
- Visualize execution timelines
- View conversation messages and flow
- Track token usage and performance metrics

✅ **Evaluation**
- Automated quality assessment with built-in evaluators
- Helpfulness, Accuracy, and Goal Success Rate metrics
- Support for session-scoped and trace-scoped evaluation
- Export results and input data for analysis

✅ **Developer Experience**
- Simple CLI commands for common tasks
- Flexible configuration with YAML files
- Rich terminal output with colors and formatting
- Export to JSON/CSV for programmatic analysis

## Quick Start

### 1. Installation

```bash
pip install bedrock-agentcore-starter-toolkit
```

### 2. Configuration

Create `.bedrock_agentcore.yaml`:
```yaml
agents:
  default:
    aws:
      region: us-east-1
    bedrock_agentcore:
      agent_id: my-agent-ABC123
```

### 3. Your First Commands

```bash
# View recent traces
agentcore obs query --session-id abc123

# Visualize execution
agentcore obs visualize --session-id abc123

# Evaluate quality
agentcore eval run --session-id abc123
```

## Documentation

### Getting Started Guides

Start here if you're new to the toolkit:

- **[Observability Getting Started](./GETTING_STARTED_OBSERVABILITY.md)**
  - Complete guide to querying and visualizing agent traces
  - Learn how to debug issues and analyze performance
  - Understand spans, logs, and metrics

- **[Evaluation Getting Started](./GETTING_STARTED_EVALUATION.md)**
  - Learn how to evaluate agent quality
  - Understand different evaluators and their scores
  - Export and analyze evaluation results

- **[Quick Reference](./QUICK_REFERENCE.md)**
  - Command cheat sheet for quick lookup
  - Common workflows and examples
  - Troubleshooting guide

### Feature Documentation

Deep dives into specific features:

- **Observability**
  - [Query Guide](./observability/QUERY_GUIDE.md) - Advanced querying techniques
  - [Visualization Guide](./observability/VISUALIZATION_GUIDE.md) - Understanding trace visualizations
  - [Performance Analysis](./observability/PERFORMANCE_ANALYSIS.md) - Optimizing agent performance
  - [Troubleshooting](./observability/TROUBLESHOOTING.md) - Common issues and solutions

- **Evaluation**
  - [Evaluators Reference](./evaluation/EVALUATORS.md) - All available evaluators
  - [Interpretation Guide](./evaluation/INTERPRETATION.md) - Understanding scores
  - [CI/CD Integration](./evaluation/CICD_INTEGRATION.md) - Automated quality checks
  - [Custom Evaluators](./evaluation/CUSTOM_EVALUATORS.md) - Building your own

### API Documentation

For programmatic access:

- **[Observability API](./api/observability.md)** - ObservabilityClient reference
- **[Evaluation API](./api/evaluation.md)** - EvaluationClient reference
- **[Models](./api/models.md)** - Data model documentation
- **[Utilities](./api/utilities.md)** - Helper functions

### Examples

Practical examples and recipes:

- **[Observability Examples](./examples/observability/)** - Common observability patterns
- **[Evaluation Examples](./examples/evaluation/)** - Quality assessment workflows
- **[Integration Examples](./examples/integration/)** - Combining observability and evaluation
- **[Automation Examples](./examples/automation/)** - Scripts and pipelines

### Best Practices

Learn from experience:

- **[Observability Best Practices](./OBSERVABILITY_BEST_PRACTICES.md)**
  - Efficient querying strategies
  - Data retention and archival
  - Performance monitoring patterns

- **[Evaluation Best Practices](./EVALUATION_BEST_PRACTICES.md)**
  - When to use which evaluators
  - Interpreting results correctly
  - Building evaluation pipelines

- **[Configuration Best Practices](./CONFIGURATION_BEST_PRACTICES.md)**
  - Organizing multi-environment setups
  - Secrets management
  - Configuration patterns

## Use Cases

### Development & Testing

**Debug a failing agent interaction:**
```bash
# 1. Find the session
agentcore obs query --all-sessions --hours 1

# 2. Visualize execution
agentcore obs visualize --session-id abc123

# 3. Check conversation flow
agentcore obs messages --session-id abc123

# 4. Evaluate quality
agentcore eval run --session-id abc123
```

**Test prompt changes:**
```bash
# Before
agentcore eval run --session-id baseline -o before.json

# After changes
agentcore eval run --session-id new -o after.json

# Compare
python compare_evals.py before.json after.json
```

### Production Monitoring

**Track quality over time:**
```bash
# Hourly monitoring script
#!/bin/bash
for session in $(agentcore obs query --all-sessions --hours 1 --format json | jq -r '.sessions[].id'); do
    agentcore eval run --session-id $session -o "evals/$(date +%Y%m%d_%H)_${session}.json"
done
```

**Performance analysis:**
```bash
# Export last 24h of traces
agentcore obs query --all-sessions --days 1 --output daily_traces.json

# Analyze with Python
python analyze_performance.py daily_traces.json
```

### Quality Assurance

**Regression testing:**
```bash
# In CI/CD pipeline
agentcore eval run --session-id $TEST_SESSION -o results.json

# Check threshold
python check_quality.py results.json --threshold 0.7 || exit 1
```

**Comprehensive evaluation:**
```bash
agentcore eval run --session-id abc123 \
  -e Builtin.Helpfulness \
  -e Builtin.Accuracy \
  -e Builtin.GoalSuccessRate \
  --all-traces \
  -o comprehensive_eval.json
```

## Common Workflows

### 1. Daily Quality Check

```bash
#!/bin/bash
# daily_check.sh

DATE=$(date +%Y-%m-%d)

# Get yesterday's sessions
SESSIONS=$(agentcore obs query --all-sessions --days 1 --format json | jq -r '.sessions[].id')

# Evaluate each
for session in $SESSIONS; do
    echo "Evaluating $session..."
    agentcore eval run --session-id $session \
        -e Builtin.Helpfulness \
        -o "reports/${DATE}_${session}.json"
done

# Generate summary
python generate_daily_report.py reports/${DATE}_*.json > "reports/${DATE}_summary.txt"

# Email report
cat "reports/${DATE}_summary.txt" | mail -s "Daily Quality Report" team@example.com
```

### 2. Real-time Debugging

```bash
# Terminal 1: Watch for new sessions
watch -n 10 'agentcore obs query --all-sessions --hours 1'

# Terminal 2: When issue found, debug immediately
SESSION="abc123"
agentcore obs visualize --session-id $SESSION
agentcore obs messages --session-id $SESSION
agentcore eval run --session-id $SESSION
```

### 3. A/B Test Analysis

```bash
#!/bin/bash
# ab_test.sh

# Collect data for variant A
echo "Testing Variant A..."
for i in {1..10}; do
    # Run test, capture session ID
    SESSION=$(python run_test.py --variant A)
    agentcore eval run --session-id $SESSION -o "variant_a_${i}.json"
done

# Collect data for variant B
echo "Testing Variant B..."
for i in {1..10}; do
    SESSION=$(python run_test.py --variant B)
    agentcore eval run --session-id $SESSION -o "variant_b_${i}.json"
done

# Analyze results
python analyze_ab_test.py variant_a_*.json variant_b_*.json
```

## Architecture

### Data Flow

```
┌─────────────────┐
│  Agent Runtime  │
│                 │
│  - LLM Calls    │
│  - Tool Calls   │
│  - Messages     │
└────────┬────────┘
         │ OpenTelemetry
         │ Traces & Logs
         ↓
┌─────────────────┐
│  CloudWatch     │
│  Logs           │
│                 │
│  - Spans        │
│  - Log Events   │
└────────┬────────┘
         │
         │ Query
         ↓
┌─────────────────┐      ┌──────────────┐
│ Observability   │      │  Evaluation  │
│ Client          │──→───│  Client      │
│                 │      │              │
│ - Query         │      │ - Transform  │
│ - Transform     │      │ - Evaluate   │
│ - Visualize     │      │ - Aggregate  │
└─────────────────┘      └──────────────┘
         │                       │
         │                       │
         ↓                       ↓
┌─────────────────┐      ┌──────────────┐
│  CLI / API      │      │  Evaluation  │
│  Output         │      │  API         │
└─────────────────┘      └──────────────┘
```

### Key Components

**ObservabilityClient**
- Queries CloudWatch Logs
- Transforms to structured data
- Provides programmatic access

**EvaluationClient**
- Fetches trace data via ObservabilityClient
- Transforms to OpenTelemetry format
- Calls evaluation API
- Aggregates results

**CLI Commands**
- `agentcore obs` - Observability commands
- `agentcore eval` - Evaluation commands
- Rich terminal output
- Export capabilities

## Configuration

### Environment Variables

```bash
# AWS Configuration
export AWS_REGION=us-east-1
export AWS_PROFILE=default

# Evaluation Configuration
export AGENTCORE_EVAL_REGION=us-east-1
export AGENTCORE_EVAL_ENDPOINT=https://custom-endpoint.com
```

### Config File Structure

```yaml
# .bedrock_agentcore.yaml

# Multiple agents
agents:
  development:
    aws:
      region: us-east-1
      profile: dev
    bedrock_agentcore:
      agent_id: dev-agent-ABC123

  production:
    aws:
      region: us-west-2
      profile: prod
    bedrock_agentcore:
      agent_id: prod-agent-XYZ789

# Evaluation defaults
evaluation:
  defaults:
    evaluators:
      - Builtin.Helpfulness
    auto_export: true
    export_path: ./eval_results

# Observability defaults
observability:
  defaults:
    time_range_hours: 24
    include_runtime_logs: true
```

## Troubleshooting

### Quick Diagnostic

```bash
# Check configuration
agentcore obs config
agentcore eval config

# Test AWS access
aws sts get-caller-identity
aws logs describe-log-groups --region us-east-1

# Verify agent ID
aws bedrock-agentcore list-agents --region us-east-1
```

### Common Issues

| Issue | Symptoms | Solution |
|-------|----------|----------|
| No traces found | Empty query results | Check session ID, time range, AWS permissions |
| Permission denied | AccessDeniedException | Add CloudWatch Logs permissions |
| Empty evaluations | `{'results': []}` | Verify gen_ai attributes in traces |
| Slow queries | Long wait times | Reduce time range, cache results |
| Config not found | "No configuration file" | Create `.bedrock_agentcore.yaml` |

See **[Troubleshooting Guide](./TROUBLESHOOTING.md)** for detailed solutions.

## Contributing

We welcome contributions! See **[Contributing Guide](../CONTRIBUTING.md)** for:
- How to report bugs
- Feature request process
- Code contribution guidelines
- Documentation improvements

## Support

- **Issues**: [GitHub Issues](https://github.com/aws/bedrock-agentcore-starter-toolkit/issues)
- **Discussions**: [GitHub Discussions](https://github.com/aws/bedrock-agentcore-starter-toolkit/discussions)
- **Documentation**: [Online Docs](https://docs.aws.amazon.com/bedrock-agentcore/)

## License

This project is licensed under Apache License 2.0. See **[LICENSE](../LICENSE)** for details.

## What's New

### Latest Release

**Version 1.0.0** - Initial Release
- Complete observability suite
- Evaluation framework with built-in evaluators
- Rich CLI with visualization
- Export and analysis tools
- Comprehensive documentation

See **[CHANGELOG](../CHANGELOG.md)** for full release history.

## Roadmap

Upcoming features:
- [ ] Custom evaluator framework
- [ ] Real-time monitoring dashboard
- [ ] Automated alerting
- [ ] Batch evaluation API
- [ ] Performance benchmarking tools
- [ ] Integration with popular CI/CD platforms

See **[ROADMAP](../ROADMAP.md)** for detailed plans.

## Additional Resources

- **AWS Bedrock AgentCore**: [Service Documentation](https://docs.aws.amazon.com/bedrock-agentcore/)
- **OpenTelemetry**: [OTel Documentation](https://opentelemetry.io/)
- **Examples Repository**: [GitHub Examples](https://github.com/aws/bedrock-agentcore-examples)
- **Blog Posts**: [AWS Blog](https://aws.amazon.com/blogs/machine-learning/)

---

**Ready to get started?** Jump to:
- [Observability Getting Started](./GETTING_STARTED_OBSERVABILITY.md)
- [Evaluation Getting Started](./GETTING_STARTED_EVALUATION.md)
- [Quick Reference](./QUICK_REFERENCE.md)
