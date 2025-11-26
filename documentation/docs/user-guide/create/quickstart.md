# QuickStart: Generate Production-Ready Projects with `agentcore create`

This guide shows how to use the Amazon Bedrock AgentCore starter toolkit to scaffold complete AgentCore projects—either runtime-only or full monorepos with infrastructure-as-code (IaC).

`agentcore create` generates a working agent implementation, model client, MCP integration, and optional IaC stacks (CDK or Terraform) that provision AgentCore Runtime, Gateway, Memory, and supporting resources in AWS.

All `create` projects use the [Bedrock AgentCore SDK](https://github.com/aws/bedrock-agentcore-sdk-python/blob/main/src/bedrock_agentcore/runtime/app.py) to define an ASGI app that is deployable to the
HTTP protocol on AgentCore runtime.

---

## What You Can Generate

`agentcore create` supports two high-level project templates.

### Runtime-Only Template (`--template basic`)

Generates:

- `src/` with ready-to-run agent code
- Model loader wired for your selected provider (Anthropic, Bedrock, OpenAI, Gemini)
- Built-in function tools
- Optional MCP client
- No infrastructure code

Use this template for lightweight deployments, and quick iteration. After creation, `agentcore launch` will zip your code and deploy an AgentCore runtime
using the [direct code deployment](https://docs.aws.amazon.com/bedrock-agentcore/latest/devguide/runtime-get-started-code-deploy.html) mode.

---

### Production Template (`--template production`)

Generates:

- `src/` (agent code)
- `mcp/` (gateway tool Lambda)
- `cdk/` or `terraform/` (based on `--iac` selection)
- IaC modeling:
  - AgentCore Runtime
  - AgentCore Gateway (MCP mode)
  - Cognito OAuth2 client credentials
  - Memory resource
  - Automatic Dockerfile generation with modeled Docker Container deployment

Use this template for full end-to-end AWS deployments.

---

## Prerequisites

- Python **3.10+**
- uv installed
- AWS account with credentials configured
- For `basic` template, required permissions defined by, [Use the starter toolkit](https://docs.aws.amazon.com/bedrock-agentcore/latest/devguide/runtime-permissions.html#runtime-permissions-starter-toolkit)
- For `production` template
    - **IAM permissions** sufficient to deploy generated resources
    - **Node.js 18+** for CDK projects
    - **Terraform 1.2+** for Terraform projects

---

## Step 1: Create a New Project

Run the CLI in interactive mode:

```bash
agentcore create
````

You will be prompted for:

* Project name
* Agent SDK (AutoGen, CrewAI, LangGraph, Strands, etc.)
* Template (`basic` or `production`)
* IaC provider (CDK or Terraform, if applicable)
* Model provider
* Whether to include MCP integration
* Whether to include memory
* Whether to load defaults from `.bedrock_agentcore.yaml`

### Optional: Run agentcore create

For `production` templates you will be prompted whether to run agentcore create first.
This lets you predefine authorization, headers, memory configuration, and agent details.

---

## Step 2: Inspect the Generated Project

Your output layout depends on the selected template.

### Basic Template

```
my_project/
  src/
    main.py
    model/
    mcp_client/
  .bedrock_agentcore.yaml
  README.md
```

Includes:

* Entrypoint (`main.py`) for local or direct runtime hosting
* Model loader
* Optional MCP tools
* Function tools depending on selected SDK

---

### Production Template (IaC + Runtime)

```
my_project/
  src/
  mcp/
    lambda/handler.py
  cdk/      OR     terraform/
  .bedrock_agentcore.yaml
  README.md
```

Includes:

* Agent runtime code
* Gateway Lambda used as an MCP target
* Full IaC modeling:

  * Runtime + endpoints
  * Gateway (MCP)
  * Cognito OAuth2
  * Memory
  * Network + environment variables
  * Container packaging config

---

## Step 3: Local Development

Create and activate a virtual environment:

```bash
cd src
python3 -m venv .venv
source .venv/bin/activate   # Windows: .venv\Scripts\activate
cd ..
```

Start the local dev server:

```bash
agentcore dev
```

Invoke it from another terminal:

```bash
agentcore invoke --dev '{"prompt": "What can you do?"}'
```

Hot reload is enabled automatically.

---

## Step 4: Deploy

### Basic template

Deploy the basic template with `agentcore launch`.

If you wish to further configure your project, first run `agentcore configure`

### Production Template

#### Production Ready Checklist

Before using your generated project in a prodcution environment, consult the following checklist:

- [ ] **Security:** Ensure secrets and API keys are properly handled. AgentCore Identity or AWS Secrets Manager are secure managed solutions.
- [ ] **Build Environment:** Confirm Docker builds are being executed in the desired environment. This template uses local Docker builds by default. Consider AWS CodeBuild.
- [ ] **Observability:** After deploying, [enable AgentCore observability](https://docs.aws.amazon.com/bedrock-agentcore/latest/devguide/observability-configure.html#observability-configure-builtin) to allow OTEL span data to be published to AWS CloudWatch.
- [ ] **CI/CD:** Build your new project into a CI/CD pipeline to achieve automated builds, rollbacks, and multiple deployment environments. Consider AWS CodePipeline.
- [ ] **Access Control:** Configure access for clients to call into your AgentCore Runtime. Take advantage of the multiple endpoints (DEFAULT, PROD, DEV) created by this template.
- [ ] **Testing** Write unit tests in the generated `test/` directory. Implement E2E tests for further coverage.
- [ ] **Error Handling** Implement graceful and consistent error handling logic throughout your code.

### CDK

```
cd cdk
npm install
npm run cdk synth
npm run cdk:deploy
```

Make sure Node 18+ is installed.

### Terraform

```
cd terraform
terraform init
terraform plan   # optional
terraform apply
```

Make sure Terraform 1.2+ is installed.

---

## Step 5: Test Your Deployed Agent

After deploy completes:

```bash
agentcore status
```

When all resources show **active**, invoke the deployed agent:

```bash
agentcore invoke '{"prompt": "Tell me a joke"}'
```

---

## Step 6: Clean Up

```bash
agentcore destroy
```

Or, for `production` template, delete stacks and resources using CDK/Terraform directly.

---

## Additional Notes

### Model Provider Authentication

* Bedrock clients use IAM automatically
* Third-party providers use:

  * AgentCore Identity in deployed environments
  * `.env.local` fallback in local dev (`LOCAL_DEV=1`)

For the `production` template, it is your responsibility to implement API key handling. Using Bedrock Agentcore Identity
or AWS Secrets Manager is recommended.

### MCP Tools

Generator output will provide the correct MCP adapter for your selected SDK, such as:

* AutoGen Streamable HTTP MCP adapter
* CrewAI MCP adapter
* Gateway-integrated MCP Lambda target

These are included automatically based on your selections.

For the `production` template, a custom MCP tool is defined in `mcp/lambda/handler.py`.

### A2A and MCP Protocols

MCP, and A2A the other two protocols supported by the [AgentCore Runtime Service Contract](https://docs.aws.amazon.com/bedrock-agentcore/latest/devguide/runtime-service-contract.html), are not currently supported
by the `create` tool out of the box. Adapting a `create` output for another protocol can also be considered.

---

## Next Steps

* Customize agent logic in `src/main.py`
* Add additional MCP integrations in `src/mcp_client/`
* For production template, modify your project to adhere to the production ready checklist.
* Ensure that `src/model/load.py` has your desired LLM provider configuration.

---
