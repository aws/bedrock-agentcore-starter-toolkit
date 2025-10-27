# Changelog

## [0.1.26] - 2025-10-17

### Changes

- Add direct dependency on Starlette as it is used in the OAuth2 callback local server (#290) (288e443)
- Implement 3LO Server on localhost:8081 to handle generating OAuth2 tokens (#282) (f2d33a5)
- fix(deps): restrict pydantic to versions below 2.41.3 (#280) (ec7880e)
- docs: enhance quickstart guides with improved structure and troubleshooting (#279) (19203e9)
- chore: bump version to 0.1.25 (#278) (57f1d40)

## [0.1.25] - 2025-10-13

### Changes

- docs: remove preview verbiage following Bedrock AgentCore GA release (#277) (232f172)
- chore: Add InvokeAgentRuntimeForUser permissions (#275) (9c8a50e)
- chore: bump version to 0.1.24 (#276) (316fc02)

## [0.1.24] - 2025-10-13

### Changes

- chore: remove workload access permissions from runtime execution policy (#274) (0f5ca36)
- docs: Add non-admin user permissions to quickstart (#271) (4599529)
- chore: bump version to 0.1.23 (#272) (598b292)

## [0.1.23] - 2025-10-11

### Changes

- feat: Improve multi-agent entrypoint handling (#270) (bf24fca)
- improve memory lifecycle management  (#253) (500d4f4)
- Update agentcore-quickstart-example.md (#269) (4b659b8)
- docs: streamline quickstart guide language and formatting (#268) (a269d39)
- docs: improve quickstart prerequisites and region handling (#266) (c1644df)
- chore: bump version to 0.1.22 (#263) (77bf849)

## [0.1.22] - 2025-10-09

### Changes

- Enhanced configuration management with source_path support and improved build workflow (#262) (949abae)
- feat: add request_header support for runtime config (#260) (e811f4f)
- fix: add non-interactive flag to integration tests (#261) (c99b5ee)
- Support vpc (#221) (8a9c3b4)
- chore: bump version to 0.1.21 (#259) (3e787bd)

## [0.1.21] - 2025-10-08

### Changes

- add a2a protocol notebook support (#258) (e656d63)
- Release v0.1.20 (#257) (1de8828)

## [0.1.20] - 2025-10-08

### Changes

- feat: Add A2A protocol support to AgentCore Runtime toolkit (#255) (84c9456)
- Fix documentation examples display (#254) (c699e4c)
- docs: improvements to quickstart (#247) (3ee881b)

## [0.1.19] - 2025-10-03

### Changes

- updates gateway created lambda to python 3.13 (#196) (c5e5642)
- Add explicit user creation config for Cognito pools (#218) (432898e)
- Labs (#245) (579d086)
- chore: bump version to 0.1.18 (#246) (c8d6c29)

## [0.1.18] - 2025-10-02

### Changes

- fix: add non_interactive parameter for notebooks and fix code style issues (#244) (03953bb)
- chore: bump version to 0.1.17 (#243) (99945c7)

## [0.1.17] - 2025-10-01

### Changes

- chore: sync main with PyPI version 0.1.16 (#242) (c414fe5)
- fix: initialize ConfigurationManager with non_interactive flag (#240) (3b92653)
- Add cleanup section and fix documentation links (#239) (cba1169)

## [0.1.16] - 2025-10-01

### Changes

- Update memory quickstart by @mikewrighton in #234
- chore: make doc titles more meaningful by @theumbrella1 in #229
- fix: don't fail validation for empty namespaces by @jona62 in #235

## [0.1.15] - 2025-10-01

### Changes

- Fixed test stability issues (#232) (ad5625d)
- chore: Add README for MemoryManager (#231) (b9fa36d)
- feat: Add automatic memory provisioning to Bedrock AgentCore CLI (#204) (d58b61c)
- Add required permission to retrieve OAuth2 Credential Provider client secret (#228) (6721d12)
- feat: Add validation to check to get_or_create_memory to provide a truly idempotent experience (#227) (29bab2e)
- fix: allow optional strategies on create memory (#225) (db5f2e0)
- Update Identity quickstart guide with a few corrections (#222) (6ea350f)
- feature: typed strategies and encryption_key_arn support on create_memory (#219) (7c726ce)
- Update quickstart with working example (#217) (1246704)
- feat: Add boto3.session to MemoryManager constructor (#211) (a838187)
- fix: Install mkdocs-llmstxt in deploy-docs act (#215) (80581c2)
- Release v0.1.14 (#214) (2d98f61)

## [0.1.14] - 2025-09-25

### Changes

- Fix: Runtime configure function now sets CodeBuild execution role from --code_build_execution_role parameter (#184) (7d7dffd)
- docs: Generate llm.txt via mkdocs-llmstxt (#213) (6459979)
- fix: llm.txt typo (#210) (f48ae5e)
- docs: Add llm.txt and file on runtime deployment (#202) (90dac4b)
- fix: correct pyproject.toml installation in subdirectories (#207) (ea01c65)

## [0.1.13] - 2025-09-24

### Changes

- Fix linter errors and ran formatter (#203) (64656b6)
- fix: add S3 bucket ownership verification (#194) (225dd86)
- quick start doc updates (#199) (3e9b930)
- Add ability to invoke runtime with custom headers (#200) (ba337db)
- revert dockerfile optimization (#198) (3285377)
- Added request header allowlist configuration support (#197) (7a7c65f)
- feat: change create_or_get_memory to get_or_create_memory to do the lookup before the create (#195) (ef22d20)
- Remove TestPyPI publishing step from release workflow (#186) (887e23b)
- feat: Initial commit for Memory manager (#169) (e067386)

## [0.1.12] - 2025-09-18

### Changes

- docs: address feedback and improve Runtime/Gateway documentation (#163) (a422708)
- chore: bump version to 0.1.11 (#180) (4e94d63)

## [0.1.11] - 2025-09-18


### Dependencies
- Updated to bedrock-agentcore SDK v0.1.4

## [0.1.10] - 2025-09-08

### Changes

- chore/improve invoke (#153) (824b22c)
- feat: add agentcore destroy command (#100) (0611649)
- chore: bump version to 0.1.9 (#152) (6e65256)

## [0.1.9] - 2025-09-07

### Changes

- fix: resolve regex escape sequence warnings (#151) (70d7381)
- feat(gateway): handle existing policies gracefully in _attach_policy (#140) (f372b99)
- chore: bump version to 0.1.8 (#150) (1421e48)

### Dependencies
- Updated to bedrock-agentcore SDK v0.1.3

## [0.1.8] - 2025-09-02

### Changes

- chore/cb latency optimization (#146) (3523bfa)
- chore(deps): update mkdocstrings-python requirement (#133) (8b8afb5)
- Release vv0.1.7 (b473e38)

## [0.1.7] - 2025-08-28

- Enhanced execution role permissions - Added relevant permissions for Runtime, Memory and Identity services to auto-created execution role (#132)
- Windows compatibility fix - Resolved file handle issue on Windows systems by properly closing NameTemporaryFile, fixing deployment failures with "process cannot access the file" errors (#106)
- Corrected managed policy name from AmazonBedrockAgentCoreFullAccess to BedrockAgentCoreFullAccess (#124)
- S3 permissions - Added missing S3 permissions documentation for bucket creation and lifecycle configuration (#124)
- Fixed IaC reference - Corrected typo in Infrastructure as Code reference (#124)
- Other documentation enhancements for clarity and completeness

## [0.1.6] - 2025-08-11

Updated SDK dependency to >=0.1.2 for improved thread pool handling and concurrency fixes

### Dependencies
- Updated to bedrock-agentcore SDK v0.1.2

## [0.1.5] - 2025-08-08

### Changes

- ci(deps): bump trufflesecurity/trufflehog from 3.82.3 to 3.90.3 (#99) (c055722)
- ci(deps): bump astral-sh/setup-uv from 3 to 6 (#80) (8f70a8c)
- increase botocore timeout (#108) (db90f00)
- bump the default otel dependency (#107) (4fd8429)
- bump version to 0.1.4 (#105) (a21ecfb)

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
