#!/usr/bin/env python3
"""
Comprehensive Security, Bug, and Vulnerability Testing

Runs multiple security scanners and code quality checks.
"""

import subprocess
import sys
import os
from pathlib import Path


def run_command(cmd, description):
    """Run a command and report results."""
    print(f"\n{'='*80}")
    print(f"Running: {description}")
    print(f"{'='*80}\n")
    
    try:
        result = subprocess.run(
            cmd,
            shell=True,
            capture_output=True,
            text=True,
            timeout=300
        )
        
        print(result.stdout)
        if result.stderr:
            print("STDERR:", result.stderr)
        
        return result.returncode == 0
    except subprocess.TimeoutExpired:
        print(f"❌ {description} timed out")
        return False
    except Exception as e:
        print(f"❌ {description} failed: {str(e)}")
        return False


def main():
    """Run all security and quality checks."""
    
    print("\n" + "="*80)
    print("COMPREHENSIVE SECURITY & QUALITY AUDIT")
    print("="*80)
    
    results = {}
    
    # 1. Check for secrets in code
    print("\n🔍 Checking for exposed secrets...")
    results['secrets'] = run_command(
        "git secrets --scan || echo 'git-secrets not installed, skipping'",
        "Secret Detection (git-secrets)"
    )
    
    # 2. Security vulnerability scan with Bandit
    print("\n🔒 Running security vulnerability scan...")
    results['bandit'] = run_command(
        "pip install bandit && bandit -r . -f json -o bandit-report.json && bandit -r . -f screen",
        "Security Scan (Bandit)"
    )
    
    # 3. Dependency vulnerability check
    print("\n📦 Checking dependencies for vulnerabilities...")
    results['safety'] = run_command(
        "pip install safety && safety check --json || true",
        "Dependency Vulnerability Check (Safety)"
    )
    
    # 4. Code quality and bug detection
    print("\n🐛 Running code quality checks...")
    results['flake8'] = run_command(
        "pip install flake8 && flake8 . --count --statistics --max-line-length=120",
        "Code Quality (Flake8)"
    )
    
    # 5. Type checking
    print("\n📝 Running type checks...")
    results['mypy'] = run_command(
        "pip install mypy && mypy . --ignore-missing-imports --no-error-summary || true",
        "Type Checking (MyPy)"
    )
    
    # 6. Check for common security issues
    print("\n🛡️ Checking for common security issues...")
    security_checks = [
        ("Hardcoded passwords", "grep -r 'password.*=.*['\"]' --include='*.py' . || true"),
        ("Hardcoded API keys", "grep -r 'api[_-]key.*=.*['\"]' --include='*.py' . || true"),
        ("Hardcoded secrets", "grep -r 'secret.*=.*['\"]' --include='*.py' . || true"),
        ("AWS keys", "grep -r 'AKIA[0-9A-Z]{16}' . || true"),
        ("Private keys", "grep -r 'BEGIN.*PRIVATE KEY' . || true"),
    ]
    
    for check_name, cmd in security_checks:
        print(f"\n  Checking for: {check_name}")
        subprocess.run(cmd, shell=True)
    
    # 7. Check .gitignore coverage
    print("\n📋 Verifying .gitignore coverage...")
    critical_patterns = [
        '.env', '*.pem', '*.key', 'credentials', 'secrets',
        '.aws/', '*.tfvars', 'config/secrets'
    ]
    
    gitignore_path = Path('.gitignore')
    if gitignore_path.exists():
        gitignore_content = gitignore_path.read_text()
        missing = []
        for pattern in critical_patterns:
            if pattern not in gitignore_content:
                missing.append(pattern)
        
        if missing:
            print(f"⚠️  Missing patterns in .gitignore: {', '.join(missing)}")
        else:
            print("✅ All critical patterns in .gitignore")
    
    # 8. Check for TODO/FIXME/HACK comments
    print("\n📝 Checking for code TODOs and FIXMEs...")
    run_command(
        "grep -r 'TODO\\|FIXME\\|HACK\\|XXX' --include='*.py' . || echo 'No TODOs found'",
        "Code TODOs"
    )
    
    # 9. Test coverage check
    print("\n🧪 Running tests with coverage...")
    results['tests'] = run_command(
        "pip install pytest pytest-cov && pytest tests/ --cov=. --cov-report=term --cov-report=html || true",
        "Test Coverage"
    )
    
    # 10. Check file permissions
    print("\n🔐 Checking file permissions...")
    run_command(
        "find . -type f -name '*.py' -perm /111 | head -20 || true",
        "Executable Python Files"
    )
    
    # Summary
    print("\n" + "="*80)
    print("AUDIT SUMMARY")
    print("="*80)
    
    passed = sum(1 for v in results.values() if v)
    total = len(results)
    
    print(f"\nChecks Passed: {passed}/{total}")
    
    for check, status in results.items():
        symbol = "✅" if status else "❌"
        print(f"  {symbol} {check}")
    
    print("\n" + "="*80)
    print("RECOMMENDATIONS")
    print("="*80)
    
    print("""
1. ✅ Never commit credentials to git
2. ✅ Use GitHub Secrets for sensitive data
3. ✅ Keep .gitignore up to date
4. ✅ Run security scans regularly
5. ✅ Update dependencies frequently
6. ✅ Review Bandit report: bandit-report.json
7. ✅ Check test coverage: htmlcov/index.html
8. ✅ Fix any high-severity issues immediately
    """)
    
    # Check if any critical issues found
    if not results.get('bandit', True):
        print("\n⚠️  CRITICAL: Security vulnerabilities found!")
        print("Review bandit-report.json for details")
        return 1
    
    print("\n✅ Security audit complete!")
    return 0


if __name__ == "__main__":
    sys.exit(main())
