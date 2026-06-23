import os
import glob

WORKSPACE_ROOT = os.path.abspath(os.environ.get("WORKSPACE_ROOT", "."))


def resolve_path(path: str) -> str:
    """Resolve path inside WORKSPACE_ROOT. Raises if it escapes."""
    full = os.path.abspath(os.path.join(WORKSPACE_ROOT, path))
    if not full.startswith(WORKSPACE_ROOT):
        raise Exception(f"Path escape blocked: {path}")
    return full


def read_file(path: str, start_line: int = 1, read_lines: int = 200) -> dict:
    """
    Read a file from the workspace with line numbers.
    Returns content with line numbers and has_more flag.
    """
    try:
        full = resolve_path(path)
        with open(full, "r", encoding="utf-8", errors="ignore") as f:
            lines = f.readlines()

        end = start_line - 1 + read_lines
        chunk = lines[start_line - 1:end]

        return {
            "content": "".join(
                f"{i + start_line}| {line}"
                for i, line in enumerate(chunk)
            ),
            "total_lines": len(lines),
            "has_more": end < len(lines),
            "start_line": start_line,
            "end_line": min(end, len(lines)),
        }
    except Exception as e:
        return {"error": str(e)}


def write_file(path: str, content: str) -> dict:
    """
    Write content to a file. Creates parent directories if needed.
    Goes through approval gate in agent — do not call directly for
    destructive overwrites without showing a diff first.
    """
    try:
        full = resolve_path(path)
        os.makedirs(os.path.dirname(full), exist_ok=True)

        # compute simple diff summary
        old_lines = 0
        if os.path.exists(full):
            with open(full, "r", encoding="utf-8", errors="ignore") as f:
                old_content = f.read()
            old_lines = len(old_content.splitlines())

        with open(full, "w", encoding="utf-8") as f:
            f.write(content)

        new_lines = len(content.splitlines())
        return {
            "status": "written",
            "path": path,
            "lines_before": old_lines,
            "lines_after": new_lines,
        }
    except Exception as e:
        return {"error": str(e)}


def edit_file(
    path: str,
    operation: str,
    start_line: int,
    end_line: int = None,
    content: str = None,
) -> dict:
    """
    Edit a file at specific lines.
    Operations:
      replace — replace lines start_line..end_line with content
      delete  — delete lines start_line..end_line
      append  — insert content after start_line
    Returns diff preview of first 20 lines after edit.
    """
    try:
        full = resolve_path(path)
        with open(full, "r", encoding="utf-8", errors="ignore") as f:
            lines = f.readlines()

        original = lines.copy()

        if operation == "replace":
            if content is None:
                return {"error": "replace requires content"}
            end = end_line if end_line is not None else start_line
            lines[start_line - 1:end] = [
                l if l.endswith("\n") else l + "\n"
                for l in content.splitlines()
            ]

        elif operation == "delete":
            end = end_line if end_line is not None else start_line
            del lines[start_line - 1:end]

        elif operation == "append":
            if content is None:
                return {"error": "append requires content"}
            new_lines = [
                l if l.endswith("\n") else l + "\n"
                for l in content.splitlines()
            ]
            lines[start_line:start_line] = new_lines

        else:
            return {"error": f"unknown operation '{operation}'. Use replace, delete, or append."}

        with open(full, "w", encoding="utf-8") as f:
            f.writelines(lines)

        # build a simple diff preview
        diff_lines = []
        for i, (old, new) in enumerate(
            zip(original[:20], lines[:20]), start=1
        ):
            if old != new:
                diff_lines.append(f"- {i}| {old.rstrip()}")
                diff_lines.append(f"+ {i}| {new.rstrip()}")

        return {
            "status": "edited",
            "operation": operation,
            "path": path,
            "lines_before": len(original),
            "lines_after": len(lines),
            "diff_preview": "\n".join(diff_lines) if diff_lines else "no changes in first 20 lines",
        }
    except Exception as e:
        return {"error": str(e)}


def list_files(path: str = ".", pattern: str = "*") -> dict:
    """List files in a directory matching a pattern."""
    try:
        full = resolve_path(path)
        matches = glob.glob(os.path.join(full, "**", pattern), recursive=True)
        # make relative
        rel = [os.path.relpath(m, WORKSPACE_ROOT) for m in matches]
        return {"files": sorted(rel)}
    except Exception as e:
        return {"error": str(e)}


TOOLS_SCHEMA = [
    {
        "type": "function",
        "function": {
            "name": "read_file",
            "description": (
                "Read a file from the workspace with line numbers. "
                "Use start_line and read_lines to read a specific window — "
                "don't read the whole file if you already know which lines matter. "
                "Check has_more to know if there's more content below."
            ),
            "parameters": {
                "type": "object",
                "properties": {
                    "path": {"type": "string", "description": "Path to the file."},
                    "start_line": {
                        "type": "integer",
                        "description": "Line to start reading from. Default 1.",
                    },
                    "read_lines": {
                        "type": "integer",
                        "description": "Number of lines to read. Default 200.",
                    },
                },
                "required": ["path"],
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "write_file",
            "description": (
                "Write content to a file. Creates the file if it doesn't exist. "
                "Use this for new files or full rewrites. "
                "For precise line-level changes, prefer edit_file instead."
            ),
            "parameters": {
                "type": "object",
                "properties": {
                    "path": {"type": "string", "description": "Path to write to."},
                    "content": {"type": "string", "description": "Full file content."},
                },
                "required": ["path", "content"],
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "edit_file",
            "description": (
                "Edit specific lines in a file. "
                "Operations: replace (replace lines start_line..end_line), "
                "delete (remove lines), append (insert after start_line). "
                "Prefer this over write_file for precise changes — "
                "it returns a diff preview so you can verify what changed."
            ),
            "parameters": {
                "type": "object",
                "properties": {
                    "path": {"type": "string", "description": "Path to the file."},
                    "operation": {
                        "type": "string",
                        "enum": ["replace", "delete", "append"],
                        "description": "Edit operation.",
                    },
                    "start_line": {
                        "type": "integer",
                        "description": "Line number to start the edit.",
                    },
                    "end_line": {
                        "type": "integer",
                        "description": "End line for replace/delete. Defaults to start_line.",
                    },
                    "content": {
                        "type": "string",
                        "description": "New content for replace/append operations.",
                    },
                },
                "required": ["path", "operation", "start_line"],
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "list_files",
            "description": "List files in a directory. Supports glob patterns.",
            "parameters": {
                "type": "object",
                "properties": {
                    "path": {
                        "type": "string",
                        "description": "Directory to list. Default workspace root.",
                    },
                    "pattern": {
                        "type": "string",
                        "description": "Glob pattern e.g. '*.py'. Default '*'.",
                    },
                },
            },
        },
    },
]


if __name__ == "__main__":
    # write a test file
    print("=== Test 1: write_file ===")
    print(write_file("notes/test.md", "# Test\nline 2\nline 3\n"))

    print("\n=== Test 2: read_file ===")
    print(read_file("notes/test.md"))

    print("\n=== Test 3: edit_file replace ===")
    print(edit_file("notes/test.md", "replace", 2, 2, "replaced line 2"))

    print("\n=== Test 4: edit_file append ===")
    print(edit_file("notes/test.md", "append", 3, content="appended line"))

    print("\n=== Test 5: list_files ===")
    print(list_files("notes"))