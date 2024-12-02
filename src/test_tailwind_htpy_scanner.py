import pytest
from pathlib import Path
import ast
from tailwind_htpy_scanner import TemplateVisitor, scan_file, scan_directory, generate_template_js

def test_template_visitor_class_keyword():
    """Test that the visitor finds classes in class_ keyword arguments."""
    code = """
    div(class_="bg-blue-500 text-white")
    """
    tree = ast.parse(code)
    visitor = TemplateVisitor()
    visitor.visit(tree)
    assert visitor.classes == {"bg-blue-500", "text-white"}

def test_template_visitor_dot_notation():
    """Test that the visitor finds classes in dot notation."""
    code = """
    div(".bg-red-500 .p-4")
    """
    tree = ast.parse(code)
    visitor = TemplateVisitor()
    visitor.visit(tree)
    assert visitor.classes == {"bg-red-500", "p-4"}

def test_template_visitor_mixed_syntax():
    """Test that the visitor handles mixed syntax in the same file."""
    code = """
    div(".flex .items-center",
        span(class_="text-sm font-bold"),
        p(".mx-4"))
    """
    tree = ast.parse(code)
    visitor = TemplateVisitor()
    visitor.visit(tree)
    assert visitor.classes == {"flex", "items-center", "text-sm", "font-bold", "mx-4"}

def test_scan_file(tmp_path):
    """Test scanning a complete file."""
    test_file = tmp_path / "test.py"
    test_file.write_text("""
    def my_template():
        return div(".container .mx-auto",
            h1(class_="text-2xl font-bold"),
            p(".mt-4 .text-gray-600"))
    """)
    classes = scan_file(test_file)
    assert classes == {"container", "mx-auto", "text-2xl", "font-bold", "mt-4", "text-gray-600"}

def test_scan_directory(tmp_path):
    """Test scanning multiple files in a directory."""
    (tmp_path / "template1.py").write_text("""
    div(".bg-blue-500")
    """)
    (tmp_path / "template2.py").write_text("""
    span(class_="text-white")
    """)
    classes = scan_directory(tmp_path, template_files=None)  # Explicitly pass None
    assert classes == {"bg-blue-500", "text-white"}

def test_generate_template_js(tmp_path):
    """Test generating the JavaScript output file."""
    output_file = tmp_path / "templates.js"
    classes = {"bg-blue-500", "text-white", "p-4"}
    generate_template_js(classes, output_file)

    content = output_file.read_text()
    assert "bg-blue-500" in content
    assert "text-white" in content
    assert "p-4" in content
    assert "export default templates" in content

def test_ignore_non_class_attributes():
    """Test that the visitor ignores other attributes."""
    code = """
    div(id_="myDiv", class_="bg-blue-500", data_value="test")
    """
    tree = ast.parse(code)
    visitor = TemplateVisitor()
    visitor.visit(tree)
    assert visitor.classes == {"bg-blue-500"}

def test_handle_empty_functions():
    """Test that the visitor handles functions with no arguments."""
    code = """
    div()
    span()
    """
    tree = ast.parse(code)
    visitor = TemplateVisitor()
    visitor.visit(tree)  # Should not raise any errors
    assert visitor.classes == set()

def test_handle_invalid_syntax(tmp_path):
    """Test handling of files with invalid Python syntax."""
    test_file = tmp_path / "invalid.py"
    test_file.write_text("this is not valid python")
    classes = scan_file(test_file)
    assert classes == set()
