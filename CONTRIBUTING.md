# Contributing to Bedrock AgentCore CLI Starter Toolkit

👋 Welcome! We're glad you're interested in the Bedrock AgentCore CLI Starter Toolkit.

## 🔒 Code Contribution Policy

**This repository is maintained exclusively by the AWS Bedrock AgentCore team and is not currently accepting external pull requests.**

While we appreciate your interest in contributing code, we maintain this policy to:
- Ensure code quality and security standards
- Maintain consistency with internal AWS development practices
- Align with our product roadmap and architecture decisions
- Comply with AWS security and compliance requirements

## How You Can Help

Although we don't accept code contributions, your feedback is invaluable! Here's how you can help improve the CLI Starter Toolkit:

### Report Bugs
Found something that doesn't work as expected? Please [open an issue](https://github.com/aws/bedrock-agentcore-starter-toolkit/issues/new?template=bug_report.md) with:
- A clear description of the problem
- Steps to reproduce the issue
- Expected vs actual behavior
- Environment details (OS, Python version, SDK version)
- Relevant code snippets and error messages

### Request Features
Have an idea for a new feature? Please [open a feature request](https://github.com/aws/bedrock-agentcore-starter-toolkit/issues/new?template=feature_request.md) with:
- Description of the problem you're trying to solve
- Proposed solution or feature
- Use cases and examples
- Any alternative solutions you've considered

### Improve Documentation
Spot an error or unclear explanation in our docs? Please [open a documentation issue](https://github.com/aws/bedrock-agentcore-starter-toolkit/issues/new?template=documentation.md) with:
- Link to the documentation page
- Description of the issue or improvement
- Suggested changes (if applicable)

### Share Examples
Created something cool with the CLI Starter Toolkit? While we can't accept code PRs, we'd love to hear about your use cases:
- Open a "Show and Tell" discussion in our [Discussions forum](https://github.com/aws/bedrock-agentcore-starter-toolkit/discussions)
- Share your experience and learnings
- Help other users with questions

## Issue Guidelines

When creating an issue:

1. **Search first**: Check if a similar issue already exists
2. **Use templates**: Select the appropriate issue template
3. **Be specific**: Provide as much detail as possible
4. **Stay on topic**: Keep discussions focused on the issue
5. **Be respectful**: Follow our Code of Conduct

## Security Issues

For security vulnerabilities, please **DO NOT** open a public issue. Instead:
- Email: aws-security@amazon.com
- Or use GitHub's private security advisory feature

See our [Security Policy](SECURITY.md) for more details.

## Questions and Discussions

- For questions about using the CLI Starter Toolkit, please use [GitHub Discussions](https://github.com/aws/bedrock-agentcore-starter-toolkit/discussions)
- For AWS Bedrock service questions, visit [AWS re:Post](https://repost.aws/)
- For urgent AWS support, use your [AWS Support](https://aws.amazon.com/support/) plan

## Development Setup (For AWS Team Members)

### About Package Management

This project uses [`uv`](https://docs.astral.sh/uv/) for dependency management, providing:

- ⚡ 10-100x faster package installation than pip
- 🔒 Lockfile support for reproducible builds
- 📦 Built-in virtual environment management
- 🎯 PEP 517 compliant builds

The repository includes:

- `pyproject.toml` - Project metadata and dependencies
- `uv.lock` - Locked dependency versions for reproducibility

### Initial Setup

```bash
# Clone and create virtual environment with dependencies
git clone https://github.com/aws/bedrock-agentcore-starter-toolkit.git
cd bedrock-agentcore-starter-toolkit

uv venv
source .venv/bin/activate  # On Windows: .venv\Scripts\activate
uv sync

# Install pre-commit hooks (one-time)
pre-commit install
```

That's it! You're ready to develop.

### Daily Development Workflow

Pre-commit hooks will now run automatically:

```bash
# Make your changes
vim src/bedrock_agentcore_starter_toolkit/cli/commands.py

# Commit (hooks run automatically)
git commit -m "feat: add new command"
# ↑ Formatting and linting run here (~10-20 seconds)

# Push (tests run automatically)
git push origin my-branch
# ↑ Security scanning and tests run here (~2-5 minutes)
```

### What the Hooks Check

**On every commit** (~10-20 seconds):
- ✅ Code formatting (auto-fixes with ruff)
- ✅ Import sorting (auto-fixes)
- ✅ Linting (with ruff)
- ✅ File hygiene (trailing whitespace, etc.)

**Before every push** (~2-5 minutes):
- ✅ Security scanning (bandit)
- ✅ Full test suite with coverage

### Skipping Hooks (WIP Commits)

For work-in-progress commits, you can skip checks:

```bash
git commit --no-verify -m "wip: incomplete work"
```

**Please run all checks before opening a PR!**

### Running Checks Manually

```bash
# Run all pre-commit checks
pre-commit run --all-files

# Run only pre-commit stage (fast)
pre-commit run --hook-stage pre-commit --all-files

# Run only pre-push stage (includes tests)
pre-commit run --hook-stage pre-push --all-files

# Run tests manually
uv run pytest tests/ --cov=src

# Run the CLI
uv run agentcore --help

# Add new dependencies
uv add requests

# Add development dependencies
uv add --dev pytest-mock
```

## Code of Conduct

This project adheres to the [Amazon Open Source Code of Conduct](https://aws.github.io/code-of-conduct). By participating, you're expected to uphold this code.

## Governance

This project is governed by the AWS Bedrock AgentCore team. Decisions about the project's direction, features, and releases are made internally by AWS.

## License

By engaging with this project, you agree that your contributions (issues, discussions, etc.) are submitted under the [Apache 2.0 License](LICENSE).

## 🙏 Thank You

Even though we can't accept code contributions at this time, your feedback, bug reports, and feature requests help us make the Bedrock AgentCore CLI Starter Toolkit better for everyone. We truly appreciate your involvement and support!

---

**Note**: This policy may change in the future. If we open the repository to external contributions, we'll update this document and announce the change.
