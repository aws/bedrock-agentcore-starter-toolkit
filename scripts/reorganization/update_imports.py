#!/usr/bin/env python3
"""
Import Update Script for Repository Reorganization

This script automatically updates import statements in Python files based on a
movement plan. It handles:
- Absolute imports
- Relative imports
- Import aliases
- Multi-line imports
- Dry-run mode for validation

Usage:
    python update_imports.py --movement-plan movement_plan.json [--dry-run]
"""

import ast
import json
import re
import argparse
from pathlib import Path
from typing import Dict, List, Tuple, Optional
from dataclasses import dataclass


@dataclass
class ImportUpdate:
    """Represents a single import update."""
    file_path: str
    line_number: int
    old_import: str
    new_import: str
    import_type: str  # 'import' or 'from_import'


class ImportUpdater:
    """Handles updating import statements in Python files."""
    
    def __init__(self, movement_map: Dict[str, str], root_dir: Path):
        """
        Initialize the import updater.
        
        Args:
            movement_map: Dictionary mapping old paths to new paths
            root_dir: Root directory of the repository
        """
        self.movement_map = movement_map
        self.root_dir = root_dir
        self.updates = []
        
        # Build module name mappings
        self.module_map = self._build_module_map()
    
    def _build_module_map(self) -> Dict[str, str]:
        """Build a mapping of old module names to new module names."""
        module_map = {}
        
        for old_path, new_path in self.movement_map.items():
            # Convert file paths to module names
            old_module = old_path.replace('.py', '').replace('/', '.').replace('\\', '.')
            new_module = new_path.replace('.py', '').replace('/', '.').replace('\\', '.')
            
            module_map[old_module] = new_module
            
            # Also map partial paths for submodule imports
            old_parts = old_module.split('.')
            new_parts = new_module.split('.')
            
            for i in range(1, len(old_parts) + 1):
                old_partial = '.'.join(old_parts[:i])
                new_partial = '.'.join(new_parts[:i])
                if old_partial not in module_map:
                    module_map[old_partial] = new_partial
        
        return module_map
    
    def _find_matching_module(self, import_module: str) -> Optional[str]:
        """Find the new module name for an import."""
        # Direct match
        if import_module in self.module_map:
            return self.module_map[import_module]
        
        # Check if any moved module is a parent of this import
        for old_mod, new_mod in self.module_map.items():
            if import_module.startswith(old_mod + '.'):
                # Replace the prefix
                suffix = import_module[len(old_mod):]
                return new_mod + suffix
        
        return None
    
    def update_file(self, file_path: Path) -> List[ImportUpdate]:
        """
        Update imports in a single file.
        
        Args:
            file_path: Path to the Python file
            
        Returns:
            List of ImportUpdate objects
        """
        try:
            with open(file_path, 'r', encoding='utf-8') as f:
                content = f.read()
                lines = content.splitlines()
            
            tree = ast.parse(content, filename=str(file_path))
            file_updates = []
            
            for node in ast.walk(tree):
                if isinstance(node, ast.Import):
                    # Handle 'import x' statements
                    for alias in node.names:
                        new_module = self._find_matching_module(alias.name)
                        if new_module:
                            old_import = lines[node.lineno - 1]
                            new_import = old_import.replace(alias.name, new_module)
                            
                            file_updates.append(ImportUpdate(
                                file_path=str(file_path.relative_to(self.root_dir)),
                                line_number=node.lineno,
                                old_import=old_import.strip(),
                                new_import=new_import.strip(),
                                import_type='import'
                            ))
                
                elif isinstance(node, ast.ImportFrom):
                    # Handle 'from x import y' statements
                    if node.module:
                        new_module = self._find_matching_module(node.module)
                        if new_module:
                            old_import = lines[node.lineno - 1]
                            new_import = old_import.replace(node.module, new_module)
                            
                            file_updates.append(ImportUpdate(
                                file_path=str(file_path.relative_to(self.root_dir)),
                                line_number=node.lineno,
                                old_import=old_import.strip(),
                                new_import=new_import.strip(),
                                import_type='from_import'
                            ))
            
            return file_updates
            
        except Exception as e:
            print(f"Error processing {file_path}: {e}")
            return []
    
    def apply_updates(self, file_path: Path, updates: List[ImportUpdate], dry_run: bool = False) -> bool:
        """
        Apply import updates to a file.
        
        Args:
            file_path: Path to the file
            updates: List of updates to apply
            dry_run: If True, don't actually modify the file
            
        Returns:
            True if successful, False otherwise
        """
        if not updates:
            return True
        
        try:
            with open(file_path, 'r', encoding='utf-8') as f:
                lines = f.readlines()
            
            # Apply updates (in reverse order to maintain line numbers)
            updates_sorted = sorted(updates, key=lambda u: u.line_number, reverse=True)
            
            for update in updates_sorted:
                line_idx = update.line_number - 1
                if line_idx < len(lines):
                    old_line = lines[line_idx].rstrip()
                    # Replace the import
                    lines[line_idx] = update.new_import + '\n'
            
            if not dry_run:
                with open(file_path, 'w', encoding='utf-8') as f:
                    f.writelines(lines)
            
            return True
            
        except Exception as e:
            print(f"Error applying updates to {file_path}: {e}")
            return False
    
    def scan_and_update_all(self, dry_run: bool = False) -> Dict:
        """
        Scan all Python files and update imports.
        
        Args:
            dry_run: If True, don't actually modify files
            
        Returns:
            Dictionary with update statistics
        """
        python_files = self._find_python_files()
        
        total_files = len(python_files)
        files_modified = 0
        total_updates = 0
        errors = []
        
        print(f"Scanning {total_files} Python files...")
        print()
        
        for i, file_path in enumerate(python_files, 1):
            if i % 10 == 0:
                print(f"  Processed {i}/{total_files} files...")
            
            updates = self.update_file(file_path)
            
            if updates:
                success = self.apply_updates(file_path, updates, dry_run)
                if success:
                    files_modified += 1
                    total_updates += len(updates)
                    self.updates.extend(updates)
                else:
                    errors.append(str(file_path))
        
        print(f"  Processed {total_files}/{total_files} files")
        print()
        
        return {
            'total_files_scanned': total_files,
            'files_modified': files_modified,
            'total_updates': total_updates,
            'errors': errors,
            'dry_run': dry_run
        }
    
    def _find_python_files(self) -> List[Path]:
        """Find all Python files in the repository."""
        exclude_dirs = {'.venv', '.venv2', '__pycache__', '.git', '.pytest_cache',
                       'node_modules', '.kiro', 'build', 'dist', '.eggs'}
        
        python_files = []
        for path in self.root_dir.rglob('*.py'):
            if any(excluded in path.parts for excluded in exclude_dirs):
                continue
            python_files.append(path)
        
        return sorted(python_files)
    
    def generate_report(self) -> str:
        """Generate a report of all updates."""
        if not self.updates:
            return "No import updates were needed."
        
        report_lines = [
            "=" * 80,
            "IMPORT UPDATE REPORT",
            "=" * 80,
            "",
            f"Total updates: {len(self.updates)}",
            f"Files affected: {len(set(u.file_path for u in self.updates))}",
            "",
            "=" * 80,
            "DETAILED CHANGES",
            "=" * 80,
            ""
        ]
        
        # Group by file
        by_file = {}
        for update in self.updates:
            if update.file_path not in by_file:
                by_file[update.file_path] = []
            by_file[update.file_path].append(update)
        
        for file_path in sorted(by_file.keys()):
            report_lines.append(f"\n{file_path}:")
            for update in sorted(by_file[file_path], key=lambda u: u.line_number):
                report_lines.append(f"  Line {update.line_number}:")
                report_lines.append(f"    - {update.old_import}")
                report_lines.append(f"    + {update.new_import}")
        
        return '\n'.join(report_lines)


def load_movement_plan(plan_file: Path) -> Dict[str, str]:
    """Load the movement plan from JSON file."""
    with open(plan_file, 'r') as f:
        plan = json.load(f)
    
    movement_map = {}
    
    # Extract movements from all categories
    if 'movements' in plan:
        for category, movements in plan['movements'].items():
            for movement in movements:
                if isinstance(movement, dict) and 'old_path' in movement and 'new_path' in movement:
                    movement_map[movement['old_path']] = movement['new_path']
    
    return movement_map


def main():
    """Main execution function."""
    parser = argparse.ArgumentParser(
        description='Update import statements based on file movements'
    )
    parser.add_argument(
        '--movement-plan',
        type=Path,
        default=Path('scripts/reorganization/movement_plan.json'),
        help='Path to the movement plan JSON file'
    )
    parser.add_argument(
        '--dry-run',
        action='store_true',
        help='Show what would be changed without modifying files'
    )
    parser.add_argument(
        '--output-report',
        type=Path,
        help='Path to save the update report'
    )
    
    args = parser.parse_args()
    
    print("=" * 80)
    print("Import Update Script")
    print("=" * 80)
    print()
    
    if args.dry_run:
        print("DRY RUN MODE - No files will be modified")
        print()
    
    # Load movement plan
    print(f"Loading movement plan from: {args.movement_plan}")
    movement_map = load_movement_plan(args.movement_plan)
    print(f"Loaded {len(movement_map)} file movements")
    print()
    
    if not movement_map:
        print("No file movements found in plan. Nothing to do.")
        return
    
    # Initialize updater
    root_dir = Path.cwd()
    updater = ImportUpdater(movement_map, root_dir)
    
    # Scan and update
    results = updater.scan_and_update_all(dry_run=args.dry_run)
    
    # Print results
    print("=" * 80)
    print("RESULTS")
    print("=" * 80)
    print(f"Files scanned: {results['total_files_scanned']}")
    print(f"Files modified: {results['files_modified']}")
    print(f"Total import updates: {results['total_updates']}")
    
    if results['errors']:
        print(f"Errors: {len(results['errors'])}")
        for error in results['errors']:
            print(f"  - {error}")
    
    print()
    
    # Generate and save report
    report = updater.generate_report()
    
    if args.output_report:
        with open(args.output_report, 'w') as f:
            f.write(report)
        print(f"Detailed report saved to: {args.output_report}")
    else:
        print(report)
    
    print()
    print("=" * 80)
    if args.dry_run:
        print("DRY RUN COMPLETE - No files were modified")
    else:
        print("IMPORT UPDATE COMPLETE")
    print("=" * 80)


if __name__ == "__main__":
    main()
