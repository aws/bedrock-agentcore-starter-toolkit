### main.tf
```hcl
{% include "https://raw.githubusercontent.com/awslabs/amazon-bedrock-agentcore-samples/refs/heads/main/04-infrastructure-as-code/terraform/multi-agent-runtime/main.tf" %}
```

### variables.tf
```hcl
{% include "https://raw.githubusercontent.com/awslabs/amazon-bedrock-agentcore-samples/refs/heads/main/04-infrastructure-as-code/terraform/multi-agent-runtime/variables.tf" %}
```

### outputs.tf
```hcl
{% include "https://raw.githubusercontent.com/awslabs/amazon-bedrock-agentcore-samples/refs/heads/main/04-infrastructure-as-code/terraform/multi-agent-runtime/outputs.tf" %}
```

### versions.tf
```hcl
{% include "https://raw.githubusercontent.com/awslabs/amazon-bedrock-agentcore-samples/refs/heads/main/04-infrastructure-as-code/terraform/multi-agent-runtime/versions.tf" %}
```

### iam.tf
```hcl
{% include "https://raw.githubusercontent.com/awslabs/amazon-bedrock-agentcore-samples/refs/heads/main/04-infrastructure-as-code/terraform/multi-agent-runtime/iam.tf" %}
```

### s3.tf
```hcl
{% include "https://raw.githubusercontent.com/awslabs/amazon-bedrock-agentcore-samples/refs/heads/main/04-infrastructure-as-code/terraform/multi-agent-runtime/s3.tf" %}
```

### ecr.tf
```hcl
{% include "https://raw.githubusercontent.com/awslabs/amazon-bedrock-agentcore-samples/refs/heads/main/04-infrastructure-as-code/terraform/multi-agent-runtime/ecr.tf" %}
```

### codebuild.tf
```hcl
{% include "https://raw.githubusercontent.com/awslabs/amazon-bedrock-agentcore-samples/refs/heads/main/04-infrastructure-as-code/terraform/multi-agent-runtime/codebuild.tf" %}
```

### orchestrator.tf
```hcl
{% include "https://raw.githubusercontent.com/awslabs/amazon-bedrock-agentcore-samples/refs/heads/main/04-infrastructure-as-code/terraform/multi-agent-runtime/orchestrator.tf" %}
```

### specialist.tf
```hcl
{% include "https://raw.githubusercontent.com/awslabs/amazon-bedrock-agentcore-samples/refs/heads/main/04-infrastructure-as-code/terraform/multi-agent-runtime/specialist.tf" %}
```

### buildspec-orchestrator.yml
```yaml
{% include "https://raw.githubusercontent.com/awslabs/amazon-bedrock-agentcore-samples/refs/heads/main/04-infrastructure-as-code/terraform/multi-agent-runtime/buildspec-orchestrator.yml" %}
```

### buildspec-specialist.yml
```yaml
{% include "https://raw.githubusercontent.com/awslabs/amazon-bedrock-agentcore-samples/refs/heads/main/04-infrastructure-as-code/terraform/multi-agent-runtime/buildspec-specialist.yml" %}
```

### terraform.tfvars.example
```hcl
{% include "https://raw.githubusercontent.com/awslabs/amazon-bedrock-agentcore-samples/refs/heads/main/04-infrastructure-as-code/terraform/multi-agent-runtime/terraform.tfvars.example" %}
```

### agent-orchestrator-code/Dockerfile
```dockerfile
{% include "https://raw.githubusercontent.com/awslabs/amazon-bedrock-agentcore-samples/refs/heads/main/04-infrastructure-as-code/terraform/multi-agent-runtime/agent-orchestrator-code/Dockerfile" %}
```

### agent-orchestrator-code/agent.py
```python
{% include "https://raw.githubusercontent.com/awslabs/amazon-bedrock-agentcore-samples/refs/heads/main/04-infrastructure-as-code/terraform/multi-agent-runtime/agent-orchestrator-code/agent.py" %}
```

### agent-orchestrator-code/requirements.txt
```
{% include "https://raw.githubusercontent.com/awslabs/amazon-bedrock-agentcore-samples/refs/heads/main/04-infrastructure-as-code/terraform/multi-agent-runtime/agent-orchestrator-code/requirements.txt" %}
```

### agent-specialist-code/Dockerfile
```dockerfile
{% include "https://raw.githubusercontent.com/awslabs/amazon-bedrock-agentcore-samples/refs/heads/main/04-infrastructure-as-code/terraform/multi-agent-runtime/agent-specialist-code/Dockerfile" %}
```

### agent-specialist-code/agent.py
```python
{% include "https://raw.githubusercontent.com/awslabs/amazon-bedrock-agentcore-samples/refs/heads/main/04-infrastructure-as-code/terraform/multi-agent-runtime/agent-specialist-code/agent.py" %}
```

### agent-specialist-code/requirements.txt
```
{% include "https://raw.githubusercontent.com/awslabs/amazon-bedrock-agentcore-samples/refs/heads/main/04-infrastructure-as-code/terraform/multi-agent-runtime/agent-specialist-code/requirements.txt" %}
```
