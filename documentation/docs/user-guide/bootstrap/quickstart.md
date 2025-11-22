# QuickStart: Generate Production Ready Projects with agentcore create

This tutorial shows you how to use the `agentcore create` command in the Amazon Bedrock AgentCore [starter toolkit](https://github.com/aws/bedrock-agentcore-starter-toolkit).

## What is agentcore create?

`agentcore create` is a CLI-based project generator. First, provide the CLI a project name, Agent SDK, and IaC proivder either through the interactive prompt or by specifying `--project-name`, `--sdk`, and `--iac` flags.
The command will write a project to the `cwd/project_name` directory that includes runtime code and infrastructure as code (CDK or Terraform) that models your Bedrock AgentCore project.

## Prerequisites
- **Python 3.10+** installed
- **AWS Account** with credentials configured. To configure your AWS credentials, see [Configuration and credential file settings in the AWS CLI](https://docs.aws.amazon.com/cli/latest/userguide/cli-configure-files.html).
- **Permissions** sufficient to deploy the modeled CDK or Terraform. The outputs of this tool are variable, so confirm the IAM permissions neccessary to deploy successfully.

## Step 1: Run agentcore create
Run `agentcore create` and follow the interactive prompts to name your project, select an Agent SDK, and select an IaC provider.

Optional: `agentcore create` can consume and configure project settings from `.bedrock_agentcore.yaml`. To provide those settings, first run `agentcore configure --create` to
specify agent name, authorization configuration, request header allowlist, and memory configuration. The `--create` flag streamlines the questionaire to only configure settings that `create` supports.

If `agentcore configure` is run in the standard settings with already provided source code, you can still run `agentcore create`. However, the generated project will copy over your existing source code
instead of generating source code. The IaC configuration will be simplified to create only an AgentCore runtime and a memory resource if it is specified in the `.bedrock_agentcore.yaml` spec.

Note, not all settings are supported by `create` currently. Multiple agents, IAM profiles

## Step 2: Inspect the generated monorepo
Inspect the project output. Start with `project_name/README.md`. Inspect runtime code in the `src/` directory and modeled IaC code in the `cdk/` or `terraform/` directory (depending on your selection).

## Step 3: Local dev
Create and activate a venv in your new project:

```
cd project_name/src

# If you have uv installed (recommended)
uv sync  # automatically creates .venv if not present

# pip approach
# python -m venv .venv
# source .venv/bin/activate
# pip install .

# Activate the environment (works for either)
source .venv/bin/activate

cd ..
```

Run and invoke the local server with hot-reloading of local changes:
```
python run_local_server.py

# In a new terminal session
python invoke_local_server.py "What can you do?"
```

## Step 4: Deploy

Follow the canonical steps for deploying in your chosen IaC.

CDK steps:

```
First check that Node version is >= 18:
- `node -v` → example output: `v18.19.0`
- [nvm](https://github.com/nvm-sh/nvm) is a helpful tool to manage Node versions

Make sure you have AWS credentials with sufficient permissions in your environment.

To deploy your project:

- shorthand: `cd cdk && npm install && npm run cdk synth && npm run cdk:deploy`
- navigate to the `cdk` directory: `cd cdk`
- install dependencies: `npm install`
- synth the CDK project: `npm run cdk synth`
- deploy all stacks: `npm run cdk:deploy`
```

Terraform steps:

```
First check that the `terraform` binary is installed with version >= 1.2:
- `terraform version -json | jq -r '.terraform_version'`
- Terraform install [webpage](https://developer.hashicorp.com/terraform/install)

Make sure you have AWS credentials with sufficient permissions in your environment.

- shorthand: `cd terraform && terraform init && terraform apply`
- navigate to the `terraform` directory: `cd terraform`
- download dependencies: `terraform init`
- [optional] overview resources to be deployed: `terraform plan`
- deploy to AWS: `terraform apply`
```
