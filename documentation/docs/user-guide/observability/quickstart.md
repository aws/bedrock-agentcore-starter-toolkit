# Getting Started with Observability

Amazon Bedrock AgentCore Observability helps you trace, debug, and monitor agent performance in production environments. This guide will help you get started with implementing observability features in your agent applications.

## What is AgentCore Observability?

AgentCore Observability provides:

- Detailed visualizations of each step in the agent workflow
- Real-time visibility into operational performance through CloudWatch dashboards
- Telemetry for key metrics such as session count, latency, duration, token usage, and error rates
- Rich metadata tagging and filtering for issue investigation
- Standardized OpenTelemetry (OTEL)-compatible format for easy integration with existing monitoring stacks


## Enabling Observability for AgentCore-Hosted Agents

By default, agents deployed to the AgentCore runtime automatically has Observability enabled.

## Enabling Observability for Non-AgentCore-Hosted Agents

For agents running outside of the AgentCore runtime, follow these additional steps:

### Step 1: Configure AWS Environment Variables

```bash
export AWS_ACCOUNT_ID=<account id>
export AWS_DEFAULT_REGION=<default region>
export AWS_REGION=<region>
export AWS_ACCESS_KEY_ID=<access key id>
export AWS_SECRET_ACCESS_KEY=<secret key>
```

### Step 2: Configure OpenTelemetry Environment Variables

```bash
export AGENT_OBSERVABILITY_ENABLED=true
export OTEL_PYTHON_DISTRO=aws_distro
export OTEL_PYTHON_CONFIGURATOR=aws_configurator
export OTEL_RESOURCE_ATTRIBUTES=service.name=<agent-name>,aws.log.group.names=/aws/bedrock-agentcore/runtimes/<agent-id>,cloud.resource_id=<AgentEndpointArn:AgentEndpointName>
export OTEL_EXPORTER_OTLP_LOGS_HEADERS=x-aws-log-group=/aws/bedrock-agentcore/runtimes/<agent-id>,x-aws-log-stream=runtime-logs,x-aws-metric-namespace=bedrock-agentcore
export OTEL_EXPORTER_OTLP_PROTOCOL=http/protobuf
export OTEL_TRACES_EXPORTER=otlp
```

Replace `<agent-name>` with your agent's name and `<agent-id>` with a unique identifier for your agent.

### Step 3: Propagate Session ID in OTEL Baggage

```python
from opentelemetry import baggage

ctx = baggage.set_baggage("session.id", session_id)  # Set the session.id in baggage
attach(ctx)  # Attach the context to make it active
```

## Viewing Observability Data

After implementing observability, you can view the collected data in CloudWatch:

### View Logs in CloudWatch

1. Open the [CloudWatch console](https://console.aws.amazon.com/cloudwatch/)
2. In the left navigation pane, expand **Logs** and select **Log groups**
3. Search for your agent's log group:
   - Standard logs (stdout/stderr): `/aws/bedrock-agentcore/runtimes/<agent_id>-<endpoint_name>/[runtime-logs] <UUID>`
   - OTEL structured logs: `/aws/bedrock-agentcore/runtimes/<agent_id>-<endpoint_name>/runtime-logs`

### View Traces and Spans

1. Open the [CloudWatch console](https://console.aws.amazon.com/cloudwatch/)
2. Select **Transaction Search** from the left navigation
3. Filter by service name or other criteria
4. Select a trace to view the detailed execution graph

### View Metrics

1. Open the [CloudWatch console](https://console.aws.amazon.com/cloudwatch/)
2. Select **Metrics** from the left navigation
3. Browse to the `bedrock-agentcore` namespace
4. Explore the available metrics

## Best Practices

1. **Use consistent session IDs** - Reuse the same session ID for related requests to maintain context across interactions
2. **Implement distributed tracing** - Use the provided headers to enable end-to-end tracing across your application components
3. **Add custom attributes** - Enhance your traces and metrics with custom attributes for better troubleshooting
4. **Monitor resource usage** - Pay attention to memory usage metrics to optimize your agent's performance
5. **Set up alerts** - Configure CloudWatch alarms to notify you of potential issues before they impact users
