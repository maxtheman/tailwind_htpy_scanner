#!/usr/bin/env python3
"""
Tailwind HTPy Scanner
Scans Python files for HTPy template class definitions and generates a JavaScript file
containing the Tailwind classes used in the templates.
"""

import ast
from pathlib import Path
from typing import Set, List, Optional
from watchdog.events import FileSystemEventHandler
import time
import fnmatch
import os

class TemplateVisitor(ast.NodeVisitor):
    """AST visitor that extracts class names from HTPy template code."""
    def __init__(self):
        self.classes: Set[str] = set()

    def visit_Call(self, node: ast.Call) -> None:
        """Visit function calls, looking for class_ attributes and dot notation classes."""
        # Check for class_ keyword arguments
        if hasattr(node, 'keywords'):
            for keyword in node.keywords:
                if keyword.arg == 'class_' and isinstance(keyword.value, ast.Constant):
                    classes = keyword.value.value.split()
                    self.classes.update(classes)

        # Check for dot notation (e.g., div(".class1 .class2"))
        if (isinstance(node.func, ast.Name) and
            node.args and
            isinstance(node.args[0], ast.Constant) and
            isinstance(node.args[0].value, str) and
            node.args[0].value.startswith('.')):
            # Remove leading dots and split on whitespace or dots
            classes = [c.lstrip('.') for c in node.args[0].value.split()]
            self.classes.update(classes)

        self.generic_visit(node)

def scan_file(file_path: Path) -> Set[str]:
    """
    Scan a single Python file for HTPy class definitions.

    Args:
        file_path: Path to the Python file to scan

    Returns:
        Set[str]: Set of Tailwind class names found in the file
    """
    try:
        with open(file_path) as f:
            tree = ast.parse(f.read())
            visitor = TemplateVisitor()
            visitor.visit(tree)
            return visitor.classes
    except SyntaxError:
        print(f"Error parsing {file_path}")
        return set()
    except Exception as e:
        print(f"Error scanning {file_path}: {e}")
        return set()

def scan_directory(directory: Path, template_files: Optional[List[str]] = None) -> Set[str]:
    """
    Scan directory for Python files containing HTPy templates.

    Args:
        directory: Base directory to scan
        template_files: Optional list of specific template files to scan

    Returns:
        Set[str]: Set of all unique Tailwind class names found
    """
    all_classes = set()

    if template_files:
        # Scan only specific template files
        for file_name in template_files:
            file_path = directory / file_name
            if file_path.exists():
                print(f"Scanning {file_path}")
                classes = scan_file(file_path)
                all_classes.update(classes)
    else:
        # Scan all Python files in directory
        for file_path in directory.rglob("*.py"):
            if not any(part.startswith('.') for part in file_path.parts) and \
               not should_ignore_path(file_path, directory):
                print(f"Scanning {file_path}")
                classes = scan_file(file_path)
                all_classes.update(classes)

    return all_classes

def should_ignore_path(path: Path, base_dir: Path) -> bool:
    """
    Check if a path should be ignored based on .gitignore patterns.

    Args:
        path: The path to check
        base_dir: The base directory containing the .gitignore file

    Returns:
        bool: True if the path should be ignored, False otherwise
    """
    gitignore_path = base_dir / '.gitignore'
    if not gitignore_path.exists():
        return False

    # Get relative path for matching
    try:
        relative_path = str(path.relative_to(base_dir))
    except ValueError:
        return False

    # Read and process gitignore patterns
    patterns = [
        line.strip()
        for line in gitignore_path.read_text().splitlines()
        if line.strip() and not line.startswith('#')
    ]

    for pattern in patterns:
        # Handle directory patterns
        if pattern.endswith('/'):
            if any(part == pattern[:-1] for part in path.parts):
                return True
            pattern_path = str(Path(pattern))
            if relative_path.startswith(pattern_path):
                return True

        # Handle absolute paths (starting with /)
        elif pattern.startswith('/'):
            clean_pattern = pattern[1:]  # Remove leading slash
            if relative_path == clean_pattern or relative_path.startswith(f"{clean_pattern}/"):
                return True

        # Handle file patterns
        else:
            # Test the pattern against the full path and all subdirectories
            if fnmatch.fnmatch(relative_path, pattern) or \
               fnmatch.fnmatch(relative_path, f"**/{pattern}") or \
               (pattern.endswith('/') and any(fnmatch.fnmatch(part, pattern[:-1]) for part in path.parts)):
                return True

    return False

def main(base_dir: Optional[Path] = None, template_files: Optional[List[str]] = None, watch: bool = False):
    """
    Main entry point for the scanner.

    Args:
        base_dir: Base directory to scan (defaults to parent of script directory)
        template_files: Optional list of specific template files to scan
        watch: Whether to watch for file changes
    """
    if base_dir is None:
        base_dir = Path(__file__).parent.parent

    output_dir = base_dir / "frontend" / "src"
    output_dir.mkdir(parents=True, exist_ok=True)
    output_file = output_dir / "templates.js"

    def scan_and_generate():
        print(f"Scanning directory: {base_dir}")
        print(f"Template files: {template_files}")
        classes = scan_directory(base_dir, template_files)
        generate_template_js(classes, output_file)
        print(f"Generated {output_file} with {len(classes)} unique classes")

    scan_and_generate()

    if watch:
        from watchdog.observers import Observer

        handler = TemplateHandler(base_dir, template_files, output_file)
        observer = Observer()
        observer.schedule(handler, str(base_dir), recursive=True)
        observer.start()

        try:
            while True:
                time.sleep(1)
        except KeyboardInterrupt:
            observer.stop()
            observer.join()


class TemplateHandler(FileSystemEventHandler):
    """Handler for template file changes."""
    def __init__(self, base_dir: Path, template_files: Optional[List[str]], output_file: Path):
        self.base_dir = base_dir
        self.template_files = template_files
        self.output_file = output_file

    def on_modified(self, event):
        """Handle file modification events."""
        if event.src_path.endswith('.py'):
            print(f"Detected change in {event.src_path}")
            classes = scan_directory(self.base_dir, self.template_files)
            generate_template_js(classes, self.output_file)

def generate_template_js(classes: Set[str], output_path: Path) -> None:
    """
    Generate a JavaScript file containing template classes for Tailwind.

    Args:
        classes: Set of class names to include
        output_path: Path where the JavaScript file should be written
    """
    js_content = f"""// Generated by template scanner - do not edit directly
const templates = `
{' '.join(sorted(classes))}
`;

export default templates;
"""
    output_path.write_text(js_content)
    print(f"Found classes: {', '.join(sorted(classes))}")

if __name__ == "__main__":
    import argparse

    parser = argparse.ArgumentParser(description="Scan HTPy templates for Tailwind classes")
    parser.add_argument('--dir', type=Path, help='Base directory to scan')
    parser.add_argument('--files', nargs='+', help='Specific template files to scan')
    parser.add_argument('--watch', action='store_true', help='Watch for file changes')

    args = parser.parse_args()

    main(args.dir, args.files, args.watch)
