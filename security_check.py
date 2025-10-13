#!/usr/bin/env python3
"""
Simple Security Check for Windows
Checks for common security issues without external dependencies.
"""

import os
import re
from pathlib import Path


def check_for_secrets():
    """Check for exposed secrets in code."""
    print("\n🔍 Checking for exposed secrets...")
    
    patterns = {
        'AWS Access Key': r'AKIA[0-9A-Z]{16}',
        'Private Key': r'BEGIN.*PRIVATE KEY',
        'Password': r'password\s*=\s*["\'][^"\']+["\']',
        'API Key': r'api[_-]key\s*=\s*["\'][^"\']+["\']',
        'Secret': r'secret\s*=\s*["\'][^"\']+["\']',
    }
    
    issues_found = []
    exclude_dirs = {'.git', '.venv', 'venv', 'node_modules', '__pycache__', 'dist', '.pytest_cache'}
    
    for root, dirs, files in os.walk('.'):
        # Remove excluded directories
        dirs[:] = [d for d in dirs if d not in exclude_dirs]
        
        for file in files:
            if file.endswith('.py'):
                filepath = Path(root) / file
                try:
                    content = filepath.read_text(encoding='utf-8', errors='ignore')
                    
                    for name, pattern in patterns.items():
                        matches = re.findall(pattern, content, re.IGNORECASE)
                        if matches:
                            issues_found.append(f"  ⚠️  {name} found in {filepath}")
                except Exception as e:
                    pass
    
    if issues_found:
        print("❌ Security issues found:")
        for issue in issues_found:
            print(issue)
        return False
    else:
        print("✅ No obvious secrets found in code")
        return True


def check_gitignore():
    """Check .gitignore coverage."""
    print("\n📋 Checking .gitignore...")
    
    critical_patterns = [
        '.env', '*.pem', '*.key', 'credentials', 'secrets',
        '.aws/', '*.tfvars', '*password*', '*token*'
    ]
    
    gitignore_path = Path('.gitignore')
    if not gitignore_path.exists():
        print("❌ .gitignore not found!")
        return False
    
    content = gitignore_path.read_text()
    missing = [p for p in critical_patterns if p not in content]
    
    if missing:
        print(f"⚠️  Missing patterns: {', '.join(missing)}")
        return False
    else:
        print("✅ .gitignore has all critical patterns")
        return True


def check_dangerous_functions():
    """Check for dangerous Python functions."""
    print("\n🐍 Checking for dangerous functions...")
    
    dangerous = {
        'eval(': 'Can execute arbitrary code',
        'exec(': 'Can execute arbitrary code',
        'pickle.loads': 'Can execute arbitrary code',
        '__import__': 'Dynamic imports can be dangerous',
    }
    
    issues = []
    exclude_dirs = {'.git', '.venv', 'venv', 'node_modules', '__pycache__', 'dist'}
    
    for root, dirs, files in os.walk('.'):
        dirs[:] = [d for d in dirs if d not in exclude_dirs]
        
        for file in files:
            if file.endswith('.py'):
                filepath = Path(root) / file
                try:
                    content = filepath.read_text(encoding='utf-8', errors='ignore')
                    
                    for func, reason in dangerous.items():
                        if func in content:
                            issues.append(f"  ⚠️  {func} in {filepath} - {reason}")
                except Exception:
                    pass
    
    if issues:
        print("⚠️  Potentially dangerous functions found:")
        for issue in issues[:10]:  # Limit output
            print(issue)
        return False
    else:
        print("✅ No dangerous functions found")
        return True


def check_env_files():
    """Check for .env files."""
    print("\n🔐 Checking for .env files...")
    
    env_files = []
    for root, dirs, files in os.walk('.'):
        if '.git' in dirs:
            dirs.remove('.git')
        if '.venv' in dirs:
            dirs.remove('.venv')
            
        for file in files:
            if file.startswith('.env') and file != '.env.example':
                env_files.append(Path(root) / file)
    
    if env_files:
        print("⚠️  .env files found (should be in .gitignore):")
        for f in env_files:
            print(f"    {f}")
        return False
    else:
        print("✅ No .env files found")
        return True


def check_github_workflow():
    """Check GitHub workflow for security."""
    print("\n🔧 Checking GitHub Actions workflow...")
    
    workflow_path = Path('.github/workflows/ci-cd.yml')
    if not workflow_path.exists():
        print("⚠️  No CI/CD workflow found")
        return True
    
    content = workflow_path.read_text()
    
    issues = []
    
    # Check for hardcoded secrets
    if re.search(r'AKIA[0-9A-Z]{16}', content):
        issues.append("  ❌ AWS keys hardcoded in workflow!")
    
    # Check for proper secret usage
    if 'secrets.' in content:
        print("  ✅ Using GitHub Secrets")
    
    # Check for security scanning
    if 'bandit' in content or 'security' in content.lower():
        print("  ✅ Security scanning configured")
    
    if issues:
        for issue in issues:
            print(issue)
        return False
    else:
        print("✅ Workflow looks secure")
        return True


def main():
    """Run all security checks."""
    print("="*80)
    print("SECURITY AUDIT")
    print("="*80)
    
    results = {
        'Secrets Check': check_for_secrets(),
        '.gitignore Check': check_gitignore(),
        'Dangerous Functions': check_dangerous_functions(),
        '.env Files': check_env_files(),
        'GitHub Workflow': check_github_workflow(),
    }
    
    print("\n" + "="*80)
    print("SUMMARY")
    print("="*80)
    
    passed = sum(1 for v in results.values() if v)
    total = len(results)
    
    print(f"\nChecks Passed: {passed}/{total}\n")
    
    for check, status in results.items():
        symbol = "✅" if status else "❌"
        print(f"  {symbol} {check}")
    
    print("\n" + "="*80)
    print("SECURITY RECOMMENDATIONS")
    print("="*80)
    print("""
1. ✅ Never commit credentials to git
2. ✅ Use GitHub Secrets for AWS keys
3. ✅ Keep .gitignore comprehensive
4. ✅ Review code for hardcoded secrets
5. ✅ Use environment variables for config
6. ✅ Enable branch protection rules
7. ✅ Require code reviews for main branch
8. ✅ Run security scans in CI/CD
    """)
    
    if passed == total:
        print("✅ All security checks passed!")
        return 0
    else:
        print(f"⚠️  {total - passed} security issues found")
        return 1


if __name__ == "__main__":
    exit(main())
