import os
import re
from collections import defaultdict, Counter
import json

# Heuristic regexes
PY_IMPORT_RE = re.compile(r'^\s*(?:from\s+([\w\.]+)\s+import|import\s+([\w\.]+))', re.MULTILINE)
JS_IMPORT_RE = re.compile(r'^\s*(?:import\s+(?:.+?\s+from\s+)?[\'"](.+?)[\'"]|require\([\'"](.+?)[\'"]\))', re.MULTILINE)
HTML_SCRIPT_RE = re.compile(r'<script[^>]*\ssrc=["\']([^"\']+)["\']', re.IGNORECASE)
HTML_LINK_RE = re.compile(r'<link[^>]*\shref=["\']([^"\']+)["\']', re.IGNORECASE)

EXT_LANG = {
    '.py': 'Python',
    '.js': 'JavaScript',
    '.jsx': 'JavaScript',
    '.ts': 'TypeScript',
    '.tsx': 'TypeScript',
    '.html': 'HTML',
    '.css': 'CSS',
    '.md': 'Markdown',
    '.json': 'JSON',
    '.yaml': 'YAML',
    '.yml': 'YAML',
    '.java': 'Java',
    '.c': 'C',
    '.cpp': 'C++',
    '.go': 'Go'
}


def ext(path):
    idx = path.rfind('.')
    return path[idx:] if idx != -1 else ''


def detect_language(path):
    e = ext(path).lower()
    return EXT_LANG.get(e, 'Other')


def analyze_repo_tree(files_info, repo_owner="", repo_name="", branch=""):
    """
    files_info: list of dicts with keys path, size, content(optional)
    returns: dict with file tree, stats, nodes, edges
    """
    stats = {"total_files": 0, "total_bytes": 0, "languages": Counter(), "total_lines": 0}
    file_by_path = {}
    for f in files_info:
        path = f['path']
        size = f.get('size', 0) or 0
        language = detect_language(path)
        content = f.get('content')
        lines = content.count('\n') + 1 if content else 0
        stats["total_files"] += 1
        stats["total_bytes"] += size
        stats["total_lines"] += lines
        stats["languages"][language] += size
        file_by_path[path] = {
            "path": path,
            "size": size,
            "language": language,
            "content": content,
            "lines": lines
        }

    # Build a folder tree for the front end
    tree = {}
    for path, info in file_by_path.items():
        parts = path.split('/')
        node = tree
        for p in parts[:-1]:
            node = node.setdefault(p, {})
        node[parts[-1]] = {"_meta": {"size": info["size"], "language": info["language"], "lines": info["lines"]}}

    # Find relationships by scanning file contents for imports, requires, script/link tags
    nodes = []
    edges = []
    path_set = set(file_by_path.keys())

    # helper to resolve relative paths (simple)
    def resolve_relative(base_path, rel):
        if rel.startswith(('.', '/')):
            base_dir = '/'.join(base_path.split('/')[:-1])
            candidate = os.path.normpath(base_dir + '/' + rel)
            # trim leading ./ if present
            candidate = candidate.lstrip('./')
            # try common extensions if missing
            if candidate in path_set:
                return candidate
            for ext_try in ['.py', '.js', '.jsx', '.ts', '.tsx', '.html']:
                if candidate + ext_try in path_set:
                    return candidate + ext_try
        else:
            # bare module names: try to map module to path heuristically
            # e.g., package.module -> package/module.py
            cand = rel.replace('.', '/') + '.py'
            if cand in path_set:
                return cand
            cand2 = rel + '.js'
            if cand2 in path_set:
                return cand2
        return None

    # Prepare nodes
    for path, info in file_by_path.items():
        nodes.append({
            "id": path,
            "label": path.split('/')[-1],
            "group": info["language"],
            "size": info["size"],
            "lines": info["lines"]
        })

    # Scan each file for references
    for path, info in file_by_path.items():
        content = info.get("content") or ""
        # Python
        for m in PY_IMPORT_RE.finditer(content):
            mod = m.group(1) or m.group(2)
            if not mod:
                continue
            target = resolve_relative(path, mod)
            if target:
                edges.append({"source": path, "target": target, "type": "py-import"})

        # JavaScript / TypeScript
        for m in JS_IMPORT_RE.finditer(content):
            rel = m.group(1) or m.group(2)
            if not rel:
                continue
            # ignore libraries like 'react' without relative path
            target = None
            if rel.startswith(('.', '/')):
                target = resolve_relative(path, rel)
            else:
                # try map to top-level file
                target = resolve_relative(path, rel)
            if target:
                edges.append({"source": path, "target": target, "type": "js-import"})

        # HTML references
        for m in HTML_SCRIPT_RE.finditer(content):
            src = m.group(1)
            target = resolve_relative(path, src)
            if target:
                edges.append({"source": path, "target": target, "type": "html-script"})
        for m in HTML_LINK_RE.finditer(content):
            href = m.group(1)
            target = resolve_relative(path, href)
            if target:
                edges.append({"source": path, "target": target, "type": "html-link"})

    # Summaries
    top_files = sorted(list(file_by_path.values()), key=lambda x: x["size"], reverse=True)[:20]
    language_bytes = dict(stats["languages"])

    return {
        "stats": {
            "total_files": stats["total_files"],
            "total_bytes": stats["total_bytes"],
            "total_lines": stats["total_lines"],
            "languages": language_bytes
        },
        "tree": tree,
        "nodes": nodes,
        "edges": edges,
        "top_files": top_files
    }
