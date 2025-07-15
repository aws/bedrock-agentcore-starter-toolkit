# Security Policy

## Reporting Security Issues

At AWS, we take security seriously. We appreciate your efforts to responsibly disclose your findings and will make every effort to acknowledge your contributions.

To report a security issue, please use one of the following methods:

### Option 1: Report through AWS Security
Please report security issues to AWS Security via:
- **Email**: [aws-security@amazon.com](mailto:aws-security@amazon.com)
- **Web**: [AWS Vulnerability Reporting](https://aws.amazon.com/security/vulnerability-reporting/)

### Option 2: Create a Private Security Advisory
For non-critical issues, you may also use GitHub's private security advisory feature:
1. Go to the Security tab of this repository
2. Click on "Report a vulnerability"
3. Fill out the form with details about the vulnerability

## What to Include in Your Report

Please include the following information to help us better understand the nature and scope of the issue:

- **Type of issue** (e.g., buffer overflow, SQL injection, cross-site scripting, credential exposure, etc.)
- **Full paths of source file(s) related to the issue**
- **Location of the affected source code** (tag/branch/commit or direct URL)
- **Any special configuration required to reproduce the issue**
- **Step-by-step instructions to reproduce the issue**
- **Proof-of-concept or exploit code** (if possible)
- **Impact of the issue**, including how an attacker might exploit it
- **Any potential mitigations you've identified**

## Response Timeline

We will acknowledge receipt of your vulnerability report within **3 business days** and send a more detailed response within **7 business days** indicating the next steps in handling your report. After the initial reply to your report, we will keep you informed of the progress towards a fix and full announcement.

## Supported Versions

We provide security updates for the following versions:

| Version | Supported          |
| ------- | ------------------ |
| Latest release | ✅ |
| Previous minor release | ✅ |
| Older versions | ❌ |

## Security Best Practices

When using the Bedrock AgentCore CLI Starter Toolkit:

### 1. **Credential Management**
- Never hardcode AWS credentials in your code
- Use AWS IAM roles and instance profiles when possible
- Rotate credentials regularly
- Use AWS Secrets Manager or Parameter Store for sensitive configuration

### 2. **OAuth Token Security**
- Store OAuth tokens securely using appropriate secret management services
- Never log or expose OAuth tokens
- Implement token rotation where supported
- Use short-lived tokens when possible

### 3. **Container Security**
- Keep base images updated with security patches
- Scan container images for vulnerabilities before deployment
- Use minimal base images to reduce attack surface
- Never store secrets in container images

### 4. **IAM Best Practices**
- Follow the principle of least privilege for execution roles
- Use session tags for fine-grained access control
- Regularly audit and review IAM permissions
- Use service control policies (SCPs) where applicable

### 5. **Network Security**
- Use VPC endpoints when available
- Implement proper security group rules
- Enable VPC Flow Logs for monitoring
- Use TLS 1.2 or higher for all communications

## Vulnerability Disclosure Policy

- Security vulnerabilities will be disclosed via GitHub Security Advisories
- We will provide credit to security researchers who responsibly disclose vulnerabilities (unless they prefer to remain anonymous)
- We request a 90-day disclosure timeline to allow for patching and distribution

## Security Updates

Security updates will be released as:
- **Critical**: Immediate patch release
- **High**: Within 30 days
- **Medium**: Within 60 days
- **Low**: Next regular release cycle

Subscribe to our security announcements by watching this repository and enabling security alerts.

## Additional Resources

- [AWS Security Center](https://aws.amazon.com/security/)
- [AWS Well-Architected Security Pillar](https://docs.aws.amazon.com/wellarchitected/latest/security-pillar/welcome.html)
- [Bedrock Security Best Practices](https://docs.aws.amazon.com/bedrock/latest/userguide/security.html)

---

**Note**: This repository is maintained by AWS and is not currently accepting external code contributions. Please report issues through the channels described above.
