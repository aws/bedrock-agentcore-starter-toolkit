#!/bin/bash
# Quick Security Check Script

echo "=================================="
echo "QUICK SECURITY CHECK"
echo "=================================="

# Check for exposed secrets
echo -e "\n🔍 Checking for exposed secrets..."
echo "Checking for AWS keys..."
grep -r "AKIA[0-9A-Z]\{16\}" . --exclude-dir={.git,.venv,node_modules,dist} 2>/dev/null && echo "⚠️  AWS keys found!" || echo "✅ No AWS keys found"

echo -e "\nChecking for private keys..."
grep -r "BEGIN.*PRIVATE KEY" . --exclude-dir={.git,.venv,node_modules,dist} 2>/dev/null && echo "⚠️  Private keys found!" || echo "✅ No private keys found"

echo -e "\nChecking for hardcoded passwords..."
grep -r "password\s*=\s*['\"]" --include="*.py" . --exclude-dir={.git,.venv,node_modules,dist} 2>/dev/null && echo "⚠️  Hardcoded passwords found!" || echo "✅ No hardcoded passwords"

echo -e "\nChecking for API keys..."
grep -r "api[_-]key\s*=\s*['\"]" --include="*.py" . --exclude-dir={.git,.venv,node_modules,dist} 2>/dev/null && echo "⚠️  API keys found!" || echo "✅ No API keys found"

# Check .gitignore
echo -e "\n📋 Checking .gitignore..."
if [ -f .gitignore ]; then
    critical_patterns=(".env" "*.pem" "*.key" "credentials" "secrets")
    missing=()
    
    for pattern in "${critical_patterns[@]}"; do
        if ! grep -q "$pattern" .gitignore; then
            missing+=("$pattern")
        fi
    done
    
    if [ ${#missing[@]} -eq 0 ]; then
        echo "✅ .gitignore has all critical patterns"
    else
        echo "⚠️  Missing in .gitignore: ${missing[*]}"
    fi
else
    echo "❌ .gitignore not found!"
fi

# Check for .env files
echo -e "\n🔐 Checking for .env files..."
find . -name ".env*" -not -name ".env.example" -not -path "./.venv/*" -not -path "./.git/*" 2>/dev/null | while read file; do
    echo "⚠️  Found: $file (should be in .gitignore)"
done || echo "✅ No .env files found"

# Check Python files for common issues
echo -e "\n🐍 Checking Python files..."
echo "Files with 'eval()' (dangerous):"
grep -r "eval(" --include="*.py" . --exclude-dir={.git,.venv,node_modules,dist} 2>/dev/null | wc -l | xargs echo

echo "Files with 'exec()' (dangerous):"
grep -r "exec(" --include="*.py" . --exclude-dir={.git,.venv,node_modules,dist} 2>/dev/null | wc -l | xargs echo

echo "Files with 'pickle' (can be unsafe):"
grep -r "import pickle" --include="*.py" . --exclude-dir={.git,.venv,node_modules,dist} 2>/dev/null | wc -l | xargs echo

echo -e "\n=================================="
echo "✅ Quick security check complete!"
echo "=================================="
echo ""
echo "For comprehensive scan, run:"
echo "  python run_security_audit.py"
echo ""
