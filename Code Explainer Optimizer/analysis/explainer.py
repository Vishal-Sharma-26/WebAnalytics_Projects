import ast
from radon.visitors import ComplexityVisitor
from radon.complexity import cc_visit
from pygments import highlight
from pygments.lexers import PythonLexer
from pygments.formatters import HtmlFormatter

def explain_code(code: str, language='python'):
    if not code.strip():
        return "No code provided."
    if language != 'python':
        return "Only Python supported in this version."

    # 1) Syntax parse check
    try:
        tree = ast.parse(code)
    except SyntaxError as e:
        return f"SyntaxError: {e}"

    explanation = {}
    # 2) Extract functions and classes with docstrings
    funcs = []
    for node in ast.walk(tree):
        if isinstance(node, ast.FunctionDef):
            doc = ast.get_docstring(node) or ""
            funcs.append({
                "name": node.name,
                "lineno": node.lineno,
                "docstring": doc,
                "args": [a.arg for a in node.args.args]
            })
    explanation['functions'] = funcs

    # 3) Complexity analysis (radon)
    try:
        cc = cc_visit(code)
        complexity_summary = [{"name": c.name, "complexity": c.complexity, "lineno": c.lineno} for c in cc]
    except Exception:
        complexity_summary = []
    explanation['complexity'] = complexity_summary

    # 4) Pretty source (html) - optional
    try:
        highlighted = highlight(code, PythonLexer(), HtmlFormatter(nowrap=True))
    except Exception:
        highlighted = None
    explanation['highlighted'] = highlighted

    # 5) Human readable summary
    summary_lines = []
    summary_lines.append(f"Detected {len(funcs)} function(s).")
    high_cc = [c for c in complexity_summary if c['complexity'] >= 10]
    if high_cc:
        summary_lines.append(f"{len(high_cc)} function(s) have high cyclomatic complexity (>=10). Consider refactoring.")
    else:
        summary_lines.append("No functions with dangerously high cyclomatic complexity detected.")
    explanation['summary'] = "\n".join(summary_lines)
    return explanation