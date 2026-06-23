import ast
import os
import re

WORKSPACE_ROOT = os.path.abspath(os.environ.get("WORKSPACE_ROOT", "."))
MAX_GREP_RESULTS = 50
EXCLUDE_DIRS = {
    ".git", "node_modules", "__pycache__",
    ".venv", "venv", "dist", "build", ".mypy_cache"
}


def resolve_path(path: str) -> str | None:
    """Resolve path inside WORKSPACE_ROOT. Return None if it escapes."""
    full = os.path.realpath(os.path.join(WORKSPACE_ROOT, path))
    workspace_real = os.path.realpath(WORKSPACE_ROOT)
    if not full.startswith(workspace_real):
        return None
    return full


def _is_binary(filepath: str) -> bool:
    """Quick check — read first 1024 bytes and look for null bytes."""
    try:
        with open(filepath, "rb") as f:
            return b"\x00" in f.read(1024)
    except Exception:
        return True


def grep(
    pattern: str,
    path: str = ".",
    case_sensitive: bool = False,
    max_results: int = MAX_GREP_RESULTS,
) -> dict:
    """
    Search file contents for pattern under path.
    Returns structured matches with file, line number, and text.
    """
    resolved = resolve_path(path)
    if resolved is None:
        return {"error": "blocked: path escapes the workspace"}

    if not os.path.exists(resolved):
        return {"error": f"path not found: {path}"}

    flags = 0 if case_sensitive else re.IGNORECASE
    try:
        regex = re.compile(pattern, flags)
    except re.error as e:
        return {"error": f"invalid regex pattern: {e}"}

    matches = []
    total = 0

    # walk directory or check single file
    if os.path.isfile(resolved):
        files_to_search = [resolved]
    else:
        files_to_search = []
        for root, dirs, files in os.walk(resolved):
            # skip excluded dirs in-place
            dirs[:] = [d for d in dirs if d not in EXCLUDE_DIRS]
            for fname in files:
                files_to_search.append(os.path.join(root, fname))

    for filepath in files_to_search:
        if _is_binary(filepath):
            continue
        try:
            with open(filepath, "r", encoding="utf-8", errors="ignore") as f:
                for lineno, line in enumerate(f, start=1):
                    if regex.search(line):
                        total += 1
                        if len(matches) < max_results:
                            # make path relative to workspace
                            rel = os.path.relpath(filepath, WORKSPACE_ROOT)
                            matches.append({
                                "file": rel,
                                "line": lineno,
                                "text": line.rstrip(),
                            })
        except Exception:
            continue

    return {
        "matches": matches,
        "total_matches": total,
        "truncated": total > max_results,
    }


def list_definitions(path: str) -> dict:
    """
    Parse a Python file with ast and return every function/class declared,
    with line numbers — a structural outline without reading the full file.
    """
    resolved = resolve_path(path)
    if resolved is None:
        return {"error": "blocked: path escapes the workspace"}

    if not os.path.exists(resolved):
        return {"error": f"file not found: {path}"}

    if not resolved.endswith(".py"):
        return {"error": "list_definitions only works on .py files"}

    try:
        with open(resolved, "r", encoding="utf-8", errors="ignore") as f:
            source = f.read()
    except Exception as e:
        return {"error": f"could not read file: {e}"}

    try:
        tree = ast.parse(source)
    except SyntaxError as e:
        return {"error": f"syntax error in file: {e}"}

    definitions = []

    for node in ast.walk(tree):
        if isinstance(node, ast.ClassDef):
            definitions.append({
                "kind": "class",
                "name": node.name,
                "line": node.lineno,
                "end_line": node.end_lineno,
            })
            # also list methods inside the class
            for item in node.body:
                if isinstance(item, ast.AsyncFunctionDef):
                    definitions.append({
                        "kind": "method",
                        "name": f"{node.name}.{item.name}",
                        "line": item.lineno,
                        "end_line": item.end_lineno,
                    })
                elif isinstance(item, ast.FunctionDef):
                    definitions.append({
                        "kind": "method",
                        "name": f"{node.name}.{item.name}",
                        "line": item.lineno,
                        "end_line": item.end_lineno,
                    })

        elif isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)):
            # only top-level functions (parent is Module)
            kind = "async function" if isinstance(node, ast.AsyncFunctionDef) else "function"
            definitions.append({
                "kind": kind,
                "name": node.name,
                "line": node.lineno,
                "end_line": node.end_lineno,
            })

    # sort by line number
    definitions.sort(key=lambda x: x["line"])

    return {"definitions": definitions}


TOOLS_SCHEMA = [
    {
        "type": "function",
        "function": {
            "name": "grep",
            "description": (
                "Search file contents for a pattern across the workspace. "
                "Use this BEFORE read_file when you don't already know which "
                "file you need. Returns file, line number, and matching text. "
                "If zero results, try a broader or alternate term before "
                "reporting the pattern doesn't exist."
            ),
            "parameters": {
                "type": "object",
                "properties": {
                    "pattern": {
                        "type": "string",
                        "description": "Text or regex pattern to search for.",
                    },
                    "path": {
                        "type": "string",
                        "description": "Subdirectory to search. Default is workspace root.",
                    },
                    "case_sensitive": {
                        "type": "boolean",
                        "description": "Default false.",
                    },
                    "max_results": {
                        "type": "integer",
                        "description": f"Cap on matches returned. Default {MAX_GREP_RESULTS}.",
                    },
                },
                "required": ["pattern"],
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "list_definitions",
            "description": (
                "List every function and class declared in a Python file, "
                "with line numbers, without reading the whole file. "
                "Use this right after grep to understand a file's structure "
                "and decide which lines to read with read_file."
            ),
            "parameters": {
                "type": "object",
                "properties": {
                    "path": {
                        "type": "string",
                        "description": "Path to a Python file.",
                    },
                },
                "required": ["path"],
            },
        },
    },
]


if __name__ == "__main__":
    print("=== Test 1: grep for 'def ' ===")
    result = grep("def ", max_results=5)
    print(result)

    print("\n=== Test 2: list_definitions on this file ===")
    print(list_definitions("tools/search.py"))