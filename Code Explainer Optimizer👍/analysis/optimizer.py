import io
import ast
import astor  # optional for AST to source (you can pip install astor)
from black import FileMode, format_str

def format_code(code: str) -> str:
    try:
        return format_str(code, mode=FileMode())
    except Exception:
        return code

class SimplifyIfTrue(ast.NodeTransformer):
    # Example transform: if x == True -> if x
    def visit_Compare(self, node):
        self.generic_visit(node)
        # only handle simple cases: Name == True
        if (isinstance(node.left, ast.Name) and
            len(node.ops) == 1 and isinstance(node.ops[0], ast.Eq) and
            len(node.comparators) == 1 and isinstance(node.comparators[0], ast.Constant) and
            node.comparators[0].value is True):
            return ast.Name(id=node.left.id, ctx=ast.Load())
        return node

def optimize_code(code: str, language='python') -> str:
    if language != 'python':
        raise NotImplementedError("Only Python supported")
    # Format first
    formatted = format_code(code)
    try:
        tree = ast.parse(formatted)
    except SyntaxError:
        return formatted

    # Apply simple AST transform(s)
    tree = SimplifyIfTrue().visit(tree)
    ast.fix_missing_locations(tree)
    try:
        import astor
        new_src = astor.to_source(tree)
    except Exception:
        # fallback: use built-in
        new_src = formatted
    return new_src