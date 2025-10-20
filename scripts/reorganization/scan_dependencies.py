#!/usr/bin/env python3
"""
Dependency Scanner for Repository Reorganization

This script scans all Python files in the repository and builds a dependency graph
showing which modules import which other modules. It identifies:
- All import statements (absolute and relative)
- Circular dependencies
- External vs internal dependencies
- Module relationships

This information is critical for updating imports during reorganization.
"""

import ast
import json
from pathlib import Path
from typing import Dict, List, Set, Tuple
from collections import defaultdict


class DependencyScanner(ast.NodeVisitor):
    """AST visitor to extract import statements from Python files."""
    
    def __init__(self, file_path: Path, root_dir: Path):
        self.file_path = file_path
        self.root_dir = root_dir
        self.imports = []
        self.from_imports = []
        
    def visit_Import(self, node):
        """Handle 'import x' statements."""
        for alias in node.names:
            self.imports.append({
                'type': 'import',
                'module': alias.name,
                'alias': alias.asname,
                'line': node.lineno
            })
        self.generic_visit(node)
    
    def visit_ImportFrom(self, node):
        """Handle 'from x import y' statements."""
        module = node.module or ''
        level = node.level  # Number of dots for relative imports
        
        for alias in node.names:
            self.from_imports.append({
                'type': 'from_import',
                'module': module,
                'name': alias.name,
                'alias': alias.asname,
                'level': level,
                'line': node.lineno,
                'is_relative': level > 0
            })
        self.generic_visit(node)


def scan_file(file_path: Path, root_dir: Path) -> Dict:
    """Scan a single Python file for imports."""
    try:
        with open(file_path, 'r', encoding='utf-8') as f:
            content = f.read()
        
        tree = ast.parse(content, filename=str(file_path))
        scanner = DependencyScanner(file_path, root_dir)
        scanner.visit(tree)
        
        return {
            'file': str(file_path.relative_to(root_dir)),
            'imports': scanner.imports,
            'from_imports': scanner.from_imports,
            'total_imports': len(scanner.imports) + len(scanner.from_imports)
        }
    except Exception as e:
        return {
            'file': str(file_path.relative_to(root_dir)),
            'error': str(e),
            'imports': [],
            'from_imports': [],
            'total_imports': 0
        }


def find_python_files(root_dir: Path, exclude_dirs: Set[str] = None) -> List[Path]:
    """Find all Python files in the repository."""
    if exclude_dirs is None:
        exclude_dirs = {'.venv', '.venv2', '__pycache__', '.git', '.pytest_cache', 
                       'node_modules', '.kiro', 'build', 'dist', '.eggs'}
    
    python_files = []
    for path in root_dir.rglob('*.py'):
        # Skip excluded directories
        if any(excluded in path.parts for excluded in exclude_dirs):
            continue
        python_files.append(path)
    
    return sorted(python_files)


def build_dependency_graph(scan_results: List[Dict]) -> Dict:
    """Build a dependency graph from scan results."""
    graph = defaultdict(set)
    
    for result in scan_results:
        if 'error' in result:
            continue
            
        file_path = result['file']
        
        # Process regular imports
        for imp in result['imports']:
            module = imp['module'].split('.')[0]  # Get top-level module
            graph[file_path].add(module)
        
        # Process from imports
        for imp in result['from_imports']:
            if not imp['is_relative']:
                module = imp['module'].split('.')[0] if imp['module'] else imp['name']
                graph[file_path].add(module)
            else:
                # For relative imports, note them specially
                graph[file_path].add(f"<relative:{imp['level']}:{imp['module']}>")
    
    return dict(graph)


def find_circular_dependencies(graph: Dict[str, Set[str]], scan_results: List[Dict]) -> List[List[str]]:
    """Identify circular dependencies in the module graph."""
    # Build internal module graph (only internal imports)
    internal_modules = {result['file'].replace('.py', '').replace('/', '.').replace('\\', '.') 
                       for result in scan_results if 'error' not in result}
    
    internal_graph = defaultdict(set)
    
    for result in scan_results:
        if 'error' in result:
            continue
            
        file_module = result['file'].replace('.py', '').replace('/', '.').replace('\\', '.')
        
        for imp in result['from_imports']:
            if not imp['is_relative'] and imp['module']:
                # Check if this is an internal import
                imp_module = imp['module']
                if any(imp_module.startswith(internal_mod) or internal_mod.startswith(imp_module) 
                      for internal_mod in internal_modules):
                    internal_graph[file_module].add(imp_module)
    
    # Simple cycle detection (DFS-based)
    cycles = []
    visited = set()
    rec_stack = set()
    
    def dfs(node, path):
        visited.add(node)
        rec_stack.add(node)
        path.append(node)
        
        for neighbor in internal_graph.get(node, []):
            if neighbor not in visited:
                dfs(neighbor, path.copy())
            elif neighbor in rec_stack:
                # Found a cycle
                cycle_start = path.index(neighbor)
                cycle = path[cycle_start:] + [neighbor]
                if cycle not in cycles and len(cycle) > 2:
                    cycles.append(cycle)
        
        rec_stack.remove(node)
    
    for node in internal_graph:
        if node not in visited:
            dfs(node, [])
    
    return cycles


def generate_report(scan_results: List[Dict], graph: Dict, cycles: List[List[str]]) -> Dict:
    """Generate a comprehensive dependency report."""
    # Count statistics
    total_files = len(scan_results)
    files_with_errors = sum(1 for r in scan_results if 'error' in r)
    total_imports = sum(r['total_imports'] for r in scan_results if 'error' not in r)
    
    # Identify most imported modules
    all_imports = defaultdict(int)
    for deps in graph.values():
        for dep in deps:
            if not dep.startswith('<relative:'):
                all_imports[dep] += 1
    
    top_imports = sorted(all_imports.items(), key=lambda x: x[1], reverse=True)[:20]
    
    # Identify files with most dependencies
    files_by_deps = sorted(
        [(file, len(deps)) for file, deps in graph.items()],
        key=lambda x: x[1],
        reverse=True
    )[:20]
    
    return {
        'summary': {
            'total_files_scanned': total_files,
            'files_with_errors': files_with_errors,
            'total_import_statements': total_imports,
            'unique_modules_imported': len(all_imports),
            'circular_dependencies_found': len(cycles)
        },
        'top_imported_modules': [
            {'module': mod, 'import_count': count} 
            for mod, count in top_imports
        ],
        'files_with_most_dependencies': [
            {'file': file, 'dependency_count': count}
            for file, count in files_by_deps
        ],
        'circular_dependencies': [
            {'cycle': cycle, 'length': len(cycle)}
            for cycle in cycles
        ]
    }


def main():
    """Main execution function."""
    print("=" * 80)
    print("Repository Dependency Scanner")
    print("=" * 80)
    print()
    
    # Setup
    root_dir = Path.cwd()
    output_dir = Path("scripts/reorganization")
    output_dir.mkdir(parents=True, exist_ok=True)
    
    # Find all Python files
    print("Finding Python files...")
    python_files = find_python_files(root_dir)
    print(f"Found {len(python_files)} Python files")
    print()
    
    # Scan all files
    print("Scanning files for imports...")
    scan_results = []
    for i, file_path in enumerate(python_files, 1):
        if i % 10 == 0:
            print(f"  Scanned {i}/{len(python_files)} files...")
        result = scan_file(file_path, root_dir)
        scan_results.append(result)
    print(f"  Scanned {len(python_files)}/{len(python_files)} files")
    print()
    
    # Build dependency graph
    print("Building dependency graph...")
    graph = build_dependency_graph(scan_results)
    print(f"Built graph with {len(graph)} nodes")
    print()
    
    # Find circular dependencies
    print("Analyzing circular dependencies...")
    cycles = find_circular_dependencies(graph, scan_results)
    print(f"Found {len(cycles)} circular dependency chains")
    print()
    
    # Generate report
    print("Generating report...")
    report = generate_report(scan_results, graph, cycles)
    
    # Save detailed results
    output_file = output_dir / "dependency_analysis.json"
    with open(output_file, 'w') as f:
        json.dump({
            'scan_results': scan_results,
            'dependency_graph': {k: list(v) for k, v in graph.items()},
            'report': report
        }, f, indent=2)
    
    print(f"Detailed results saved to: {output_file}")
    print()
    
    # Print summary
    print("=" * 80)
    print("SUMMARY")
    print("=" * 80)
    print(f"Total files scanned: {report['summary']['total_files_scanned']}")
    print(f"Files with errors: {report['summary']['files_with_errors']}")
    print(f"Total import statements: {report['summary']['total_import_statements']}")
    print(f"Unique modules imported: {report['summary']['unique_modules_imported']}")
    print(f"Circular dependencies: {report['summary']['circular_dependencies_found']}")
    print()
    
    if report['top_imported_modules']:
        print("Top 10 Most Imported Modules:")
        for item in report['top_imported_modules'][:10]:
            print(f"  {item['module']}: {item['import_count']} imports")
        print()
    
    if report['circular_dependencies']:
        print("Circular Dependencies Found:")
        for item in report['circular_dependencies'][:5]:
            print(f"  Cycle length {item['length']}: {' -> '.join(item['cycle'][:3])}...")
        print()
    
    print("=" * 80)
    print("Dependency scan complete!")
    print("=" * 80)


if __name__ == "__main__":
    main()
