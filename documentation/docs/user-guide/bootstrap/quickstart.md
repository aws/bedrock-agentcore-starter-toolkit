# QuickStart: Generate Production Ready Projects with agentcore bootstrap

This tutorial shows you how to use the `agentcore bootstrap` command in the Amazon Bedrock AgentCore [starter toolkit](https://github.com/aws/bedrock-agentcore-starter-toolkit).

## What is agentcore bootstrap?

`agentcore bootstrap` is a CLI-based project generator. First, provide the CLI a project name, Agent SDK, and IaC proivder either through the interactive prompt or by specifying `--project-name`, `--sdk`, and `--iac` flags.
The command will write a project to the `cwd/project_name` directory that includes runtime code and infrastructure as code (CDK or Terraform) that models your Bedrock AgentCore project.

## Prerequisites
- **Python 3.10+** installed
- **AWS Account** with credentials configured. To configure your AWS credentials, see [Configuration and credential file settings in the AWS CLI](https://docs.aws.amazon.com/cli/latest/userguide/cli-configure-files.html).
- **Permissions** sufficient to deploy the modeled CDK or Terraform. The outputs of this tool are variable, so confirm the IAM permissions neccessary to deploy successfully.

## Step 1: Run agentcore bootstrap
Run `agentcore bootstrap` and follow the interactive prompts to name your project, select an Agent SDK, and select an IaC provider.

Optional: first run `agentcore configure --bootstrap` to specify agent name, authorization configuration, request header allowlist, and memory configuration.

## Step 2: Inspect your generated monorepo
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

CDK steps:

```
First check that Node version is >= 18:
- `node -v` → example output: `v18.19.0`
- [nvm](https://github.com/nvm-sh/nvm) is a helpful tool to manage Node versions

To deploy your project:

- shorthand: `cd cdk && npm install && npm run cdk synth && npm run cdk:deploy`
- navigate to the `cdk` directory: `cd cdk`
- install dependencies: `npm install`
- synth the CDK project: `npm run cdk synth`
- deploy all stacks: `npm run cdk:deploy`
```