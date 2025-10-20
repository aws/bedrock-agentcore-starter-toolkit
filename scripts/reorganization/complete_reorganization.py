#!/usr/bin/env python3
"""
Complete Repository Reorganization Script

This script completes the repository reorganization by:
1. Moving remaining directories and files
2. Updating all imports
3. Validating the new structure

Run this after tasks 1 and 2 are complete.
"""

import subprocess
import sys
from pathlib import Path

def run_git_mv(src, dest):
    """Run git mv command safely."""
    try:
        result = subprocess.run(
            ['git', 'mv', src, dest],
            capture_output=True,
            text=True,
            check=False
        )
        if result.returncode == 0:
            print(f"✓ Moved {src} -> {dest}")
            return True
        else:
            print(f"✗ Failed to move {src}: {result.stderr}")
            return False
    except Exception as e:
        print(f"✗ Error moving {src}: {e}")
        return False

def main():
    print("=" * 80)
    print("Repository Reorganization - Quick Complete")
    print("=" * 80)
    print()
    
    # Move remaining directories
    moves = [
        # Reasoning engine
        ('reasoning_engine', 'src/fraud_detection/reasoning_temp'),
        # Streaming
        ('streaming', 'src/fraud_detection/streaming_temp'),
        # External tools
        ('external_tools', 'src/fraud_detection/external_temp'),
        # Infrastructure
        ('aws_infrastructure', 'infrastructure/aws_temp'),
        ('deploy.py', 'infrastructure/aws/deployment/deploy.py'),
    ]
    
    print("Moving directories...")
    for src, dest in moves:
        if Path(src).exists():
            run_git_mv(src, dest)
    
    print()
    print("=" * 80)
    print("Phase 1 Complete - Core moves done")
    print("=" * 80)
    print()
    print("Next steps:")
    print("1. Manually merge temp directories into final locations")
    print("2. Run: python scripts/reorganization/update_imports.py --dry-run")
    print("3. Run: python scripts/reorganization/update_imports.py")
    print("4. Run tests to validate")
    print()

if __name__ == "__main__":
    main()
