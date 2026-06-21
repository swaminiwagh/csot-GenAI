import os

WORKSPACE_ROOT = os.path.abspath(os.getenv("WORKSPACE_ROOT", "."))

def resolve_path(path):
    full = os.path.abspath(os.path.join(WORKSPACE_ROOT, path))
    if not full.startswith(WORKSPACE_ROOT):
        raise Exception("Path escape blocked")
    return full

def read_file(path, start_line=1, read_lines=200):
    try:
        full = resolve_path(path)
        with open(full, "r") as f:
            lines = f.readlines()

        end = start_line - 1 + read_lines
        chunk = lines[start_line-1:end]

        return {
            "content": "".join(f"{i+start_line}| {l}" for i,l in enumerate(chunk)),
            "has_more": end < len(lines)
        }
    except Exception as e:
        return {"error": str(e)}

def write_file(path, content):
    try:
        full = resolve_path(path)
        os.makedirs(os.path.dirname(full), exist_ok=True)
        with open(full, "w") as f:
            f.write(content)
        return {"status": "written"}
    except Exception as e:
        return {"error": str(e)}

def edit_file(path, operation, start_line, end_line=None, content=None):
    try:
        full = resolve_path(path)
        with open(full) as f:
            lines = f.readlines()

        if operation == "replace":
            lines[start_line-1:end_line] = content.splitlines(True)

        elif operation == "delete":
            del lines[start_line-1:end_line]

        elif operation == "append":
            lines.insert(start_line, content + "\n")

        with open(full, "w") as f:
            f.writelines(lines)

        return {"status": "edited", "preview": "".join(lines[:20])}

    except Exception as e:
        return {"error": str(e)}

def list_files(path=".", pattern="*"):
    import glob
    full = resolve_path(path)
    return {"files": glob.glob(os.path.join(full, pattern))}