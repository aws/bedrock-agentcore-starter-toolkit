### app.py:
```python
{% include "https://raw.githubusercontent.com/awslabs/amazon-bedrock-agentcore-samples/refs/heads/main/04-infrastructure-as-code/cdk/basic-runtime/app.py" %}
```

### basic_runtime_stack.py
```python
{% include "https://raw.githubusercontent.com/awslabs/amazon-bedrock-agentcore-samples/refs/heads/main/04-infrastructure-as-code/cdk/basic-runtime/basic_runtime_stack.py" %}
```

### cdk.json
```
{% include "https://raw.githubusercontent.com/awslabs/amazon-bedrock-agentcore-samples/refs/heads/main/04-infrastructure-as-code/cdk/basic-runtime/cdk.json" %}
```

### requirements.txt
```
aws-cdk-lib==2.218.0
constructs>=10.0.79
```

### agentcore/Dockerfile
```
{% include "https://raw.githubusercontent.com/awslabs/amazon-bedrock-agentcore-samples/refs/heads/main/04-infrastructure-as-code/cdk/basic-runtime/agent-code/Dockerfile" %}
```

### agentcore/basic_agent.py
```python
{% include "https://raw.githubusercontent.com/awslabs/amazon-bedrock-agentcore-samples/refs/heads/main/04-infrastructure-as-code/cdk/basic-runtime/agent-code/basic_agent.py" %}
```

### infra_utils/agentcore_role.py
```python
{% include "https://raw.githubusercontent.com/awslabs/amazon-bedrock-agentcore-samples/refs/heads/main/04-infrastructure-as-code/cdk/basic-runtime/infra_utils/agentcore_role.py" %}
```

### infra_utils/build_trigger_lambda.py
```python
{% include "https://raw.githubusercontent.com/awslabs/amazon-bedrock-agentcore-samples/refs/heads/main/04-infrastructure-as-code/cdk/basic-runtime/infra_utils/build_trigger_lambda.py" %}
```