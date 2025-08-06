# Changelog

## [0.1.4] - 2025-08-06

Added a utility to import from Bedrock Agents -> Bedrock AgentCore. Developers can generate and deploy a Langchain/Strands + AgentCore agent from a selected Bedrock Agent. The output agent leverages AgentCore primitives such as Gateway, Observability, Memory, and Code Interpreter. Added documentation on usage and design of this utility. This utility does not introduce any breaking changes. It is aimed towards Bedrock Agents customers who want to try a code-first, extensible approach with AgentCore.

## [0.1.3] - 2025-08-01

### BREAKING CHANGES
- **CodeBuild is now the default launch method** - The `--codebuild` flag is no longer needed
  - To use local Docker builds, you must now explicitly use `--local-build` flag
  - This change improves the default user experience by building ARM64 containers in the cloud without requiring local Docker

### Added
- **Streaming invoke support re-enabled** - Restored streaming functionality for real-time agent responses
- **Extended request timeout** - Increased invoke request timeout from default to 900 seconds (15 minutes) to support long-running agent operations

### Changed
- **Default launch behavior** - CodeBuild is now the default (`use_codebuild=True`)
  - Users no longer need Docker installed locally for standard deployments
  - Automatic ARM64 container builds in AWS CodeBuild
  - Use `agentcore launch` for cloud builds (default)
  - Use `agentcore launch --local-build` for local Docker builds

### Improved
- **Enhanced CLI help text** - Clearer descriptions guide users toward recommended options
- **Better error messages** - Actionable recommendations for common issues
- **Conflict handling** - Enhanced exception messages now suggest using `--auto-update-on-conflict` flag


## [0.1.2] - 2025-07-23

### Fixed
- **S3 bucket creation in us-east-1 region** - Fixed CodeBuild S3 bucket creation failure
  - Removed unsupported `LocationConstraint` parameter for us-east-1 region
  - us-east-1 is the default S3 region and does not accept LocationConstraint
  - CodeBuild feature now works correctly in all AWS regions including IAD

### Dependencies
- Updated to use bedrock-agentcore SDK v0.1.1

## [0.1.1] - 2025-07-22

### Added
- **Multi-platform Docker build support via AWS CodeBuild** (#1)
  - New `--codebuild` flag for `agentcore launch` command enables ARM64 container builds
  - Complete `CodeBuildService` class with ARM64-optimized build pipeline
  - Automated infrastructure provisioning (S3 buckets, IAM roles, CodeBuild projects)
  - ARM64-optimized buildspec with Docker BuildKit caching and parallel push operations
  - Smart source management with .dockerignore pattern support and S3 lifecycle policies
  - Real-time build monitoring with detailed phase tracking
  - Support for `aws/codebuild/amazonlinux2-aarch64-standard:3.0` image
  - ECR caching strategy for faster ARM64 builds

- **Automatic IAM execution role creation** (#2)
  - Auto-creation of IAM execution roles for Bedrock AgentCore Runtime
  - Policy templates for execution role and trust policy
  - Detailed logging and progress tracking during role creation
  - Informative error messages for common IAM scenarios
  - Eliminates need for manual IAM role creation before deployment

- **Auto-update on conflict for agent deployments** (#3)
  - New `--auto-update-on-conflict` flag for `agentcore launch` command
  - Automatically updates existing agents instead of failing with conflict errors
  - Available in both CLI and notebook interfaces
  - Streamlines iterative development and deployment workflows

### Changed
- Enhanced `agentcore launch` command to support both local Docker and CodeBuild workflows
- Improved error handling patterns throughout the codebase
- Updated AWS SDK exception handling to use standard `ClientError` patterns instead of service-specific exceptions

### Fixed
- Fixed AWS IAM exception handling by replacing problematic service-specific exceptions with standard `ClientError` patterns
- Resolved pre-commit hook compliance issues with proper code formatting

### Improved
- Added 90%+ test coverage with 20+ new comprehensive test cases
- Enhanced error handling with proper AWS SDK patterns
- Improved build reliability and monitoring capabilities
- Better user experience with one-command ARM64 deployment

## [0.1.0] - 2025-07-16

### Added
- Initial release of Bedrock AgentCore Starter Toolkit
- CLI toolkit for deploying AI agents to Amazon Bedrock AgentCore
- Zero infrastructure management with built-in gateway and memory integrations
- Support for popular frameworks (Strands, LangGraph, CrewAI, custom agents)
- Core CLI commands: `configure`, `launch`, `invoke`, `status`
- Local testing capabilities with `--local` flag
- Integration with Bedrock AgentCore SDK
- Basic Docker containerization support
- Comprehensive documentation and examples
