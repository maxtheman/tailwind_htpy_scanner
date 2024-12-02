from tailwind_htpy_scanner import (
    TemplateVisitor, TemplateHandler, scan_file, scan_directory,
    generate_template_js, main, should_ignore_path
)
from unittest.mock import Mock
from watchdog.events import FileModifiedEvent
import ast
import pytest

def test_template_visitor_class_keyword():
    """Test that the visitor finds classes in class_ keyword arguments."""
    code = "div(class_='bg-blue-500 text-white')"  # Remove newlines and indentation
    tree = ast.parse(code)
    visitor = TemplateVisitor()
    visitor.visit(tree)
    assert visitor.classes == {"bg-blue-500", "text-white"}

def test_template_visitor_dot_notation():
    """Test that the visitor finds classes in dot notation."""
    code = "div('.bg-red-500 .p-4')"  # Remove newlines and indentation
    tree = ast.parse(code)
    visitor = TemplateVisitor()
    visitor.visit(tree)
    assert visitor.classes == {"bg-red-500", "p-4"}

def test_template_visitor_mixed_syntax():
    """Test that the visitor handles mixed syntax in the same file."""
    code = "div('.flex .items-center', span(class_='text-sm font-bold'), p('.mx-4'))"
    tree = ast.parse(code)
    visitor = TemplateVisitor()
    visitor.visit(tree)
    assert visitor.classes == {"flex", "items-center", "text-sm", "font-bold", "mx-4"}

def test_scan_file(tmp_path):
    """Test scanning a complete file."""
    test_file = tmp_path / "test.py"
    test_file.write_text(
        "def my_template():\n"
        "    return div('.container .mx-auto',\n"
        "        h1(class_='text-2xl font-bold'),\n"
        "        p('.mt-4 .text-gray-600'))"
    )
    classes = scan_file(test_file)
    assert classes == {"container", "mx-auto", "text-2xl", "font-bold", "mt-4", "text-gray-600"}

def test_scan_directory(tmp_path):
    """Test scanning multiple files in a directory."""
    (tmp_path / "template1.py").write_text("div('.bg-blue-500')")
    (tmp_path / "template2.py").write_text("span(class_='text-white')")
    classes = scan_directory(tmp_path)
    assert classes == {"bg-blue-500", "text-white"}

def test_handle_empty_functions():
    """Test that the visitor handles functions with no arguments."""
    code = "div()\nspan()"  # Simple, no indentation
    tree = ast.parse(code)
    visitor = TemplateVisitor()
    visitor.visit(tree)  # Should not raise any errors
    assert visitor.classes == set()

def test_ignore_non_class_attributes():
    """Test that the visitor ignores other attributes."""
    code = "div(id_='myDiv', class_='bg-blue-500', data_value='test')"
    tree = ast.parse(code)
    visitor = TemplateVisitor()
    visitor.visit(tree)
    assert visitor.classes == {"bg-blue-500"}

def test_handle_invalid_syntax(tmp_path):
    """Test handling of files with invalid Python syntax."""
    test_file = tmp_path / "invalid.py"
    test_file.write_text("this is not valid python")
    classes = scan_file(test_file)
    assert classes == set()

def test_generate_template_js(tmp_path):
    """Test generating the JavaScript output file."""
    output_file = tmp_path / "templates.js"
    classes = {"bg-blue-500", "text-white", "p-4"}
    generate_template_js(classes, output_file)

    assert output_file.exists()
    content = output_file.read_text()
    assert "// Generated by template scanner" in content
    assert "bg-blue-500" in content
    assert "text-white" in content
    assert "p-4" in content
    assert "export default templates" in content
    assert content.count("bg-blue-500") == 1  # Ensure no duplicates

def test_scan_directory_with_specific_files(tmp_path):
    """Test scanning directory with specific file list."""
    # Create multiple files but only scan some
    (tmp_path / "template1.py").write_text("div('.bg-blue-500')")
    (tmp_path / "template2.py").write_text("span(class_='text-white')")
    (tmp_path / "template3.py").write_text("div('.p-4')")

    # Only scan template1 and template2
    classes = scan_directory(tmp_path, template_files=["template1.py", "template2.py"])
    assert classes == {"bg-blue-500", "text-white"}

    # Test with file that doesn't exist
    classes = scan_directory(tmp_path, template_files=["nonexistent.py"])
    assert classes == set()

def test_watch_mode(tmp_path, monkeypatch):
    """Test the file watching functionality."""
    # Import mock here to match the import in the main function
    mock_observer = Mock()
    mock_observer_class = Mock(return_value=mock_observer)
    monkeypatch.setattr("watchdog.observers.Observer", mock_observer_class)

    # Create a test file and output directory
    test_file = tmp_path / "template.py"
    test_file.write_text("div('.test-class')")
    output_dir = tmp_path / "frontend" / "src"
    output_dir.mkdir(parents=True)

    # Mock time.sleep to avoid infinite loop
    mock_sleep = Mock(side_effect=KeyboardInterrupt)
    monkeypatch.setattr("time.sleep", mock_sleep)

    # Run main with watch mode
    try:
        main(base_dir=tmp_path, watch=True)
    except KeyboardInterrupt:
        pass

    # Verify observer was properly used
    assert mock_observer_class.called
    assert mock_observer.schedule.called
    assert mock_observer.start.called
    assert mock_observer.stop.called
    assert mock_observer.join.called

def test_scan_directory_with_gitignore(tmp_path):
    """Test that scan_directory respects .gitignore patterns."""
    # Create a .gitignore file without leading spaces
    gitignore_content = """
ignored/
*.ignored.py
""".strip()
    (tmp_path / ".gitignore").write_text(gitignore_content)

    # Create test files
    ignored_dir = tmp_path / "ignored"
    ignored_dir.mkdir()
    (ignored_dir / "template.py").write_text("div('.should-not-find')")
    (tmp_path / "test.ignored.py").write_text("div('.also-should-not-find')")
    (tmp_path / "template.py").write_text("div('.should-find')")

    # Test individual ignore checks
    assert should_ignore_path(ignored_dir / "template.py", tmp_path)
    assert should_ignore_path(tmp_path / "test.ignored.py", tmp_path)
    assert not should_ignore_path(tmp_path / "template.py", tmp_path)

    # Test full directory scan
    classes = scan_directory(tmp_path)
    assert "should-find" in classes
    assert "should-not-find" not in classes
    assert "also-should-not-find" not in classes

def test_should_ignore_path(tmp_path):
    """Test the should_ignore_path function with various patterns."""
    # Create .gitignore without leading spaces
    gitignore_content = """
*.ignored
build/
/absolute/path
relative/path/
""".strip()
    (tmp_path / ".gitignore").write_text(gitignore_content)

    # Test different path types
    assert should_ignore_path(tmp_path / "test.ignored", tmp_path)
    assert should_ignore_path(tmp_path / "build" / "any.py", tmp_path)
    assert should_ignore_path(tmp_path / "absolute" / "path" / "file.py", tmp_path)
    assert should_ignore_path(tmp_path / "relative" / "path" / "file.py", tmp_path)
    assert not should_ignore_path(tmp_path / "normal.py", tmp_path)
