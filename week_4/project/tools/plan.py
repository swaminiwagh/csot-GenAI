import json
import os
from datetime import datetime, UTC

WORKSPACE_ROOT = os.path.abspath(os.environ.get("WORKSPACE_ROOT", "."))
PROJECT_ROOT = os.path.dirname(os.path.abspath(__file__ + "/.."))
TODOS_FILE = os.path.join(PROJECT_ROOT, ".agent", "todos.json")


def _load() -> list:
    """Load todos from disk."""
    if not os.path.exists(TODOS_FILE):
        return []
    try:
        with open(TODOS_FILE, "r", encoding="utf-8") as f:
            return json.load(f)
    except Exception:
        return []


def _save(todos: list) -> None:
    """Save todos to disk."""
    os.makedirs(os.path.dirname(TODOS_FILE), exist_ok=True)
    with open(TODOS_FILE, "w", encoding="utf-8") as f:
        json.dump(todos, f, indent=2)


def add_todos(items: list) -> dict:
    """
    Add one or more todo items to the list.

    Each item must have:
      - title (string) — short name for the task
      - description (string) — what needs to be done
      - verification (string) — concrete command or check to confirm done

    Optional:
      - id (string) — auto-generated if not provided
    """
    todos = _load()

    added = []
    for item in items:
        if "title" not in item or "description" not in item:
            return {"error": "each todo must have 'title' and 'description'"}

        todo = {
            "id": item.get("id") or f"todo_{len(todos) + len(added) + 1}",
            "title": item["title"],
            "description": item["description"],
            "verification": item.get("verification", "manual check"),
            "status": "pending",
            "evidence": None,
            "created_at": datetime.now(UTC).isoformat(),
            "updated_at": datetime.utcnow().isoformat(),
        }
        todos.append(todo)
        added.append(todo)

    _save(todos)
    return {"added": added, "todos": todos}


def get_todos(status: str = None) -> dict:
    """
    Return the current todo list.
    Optionally filter by status: pending, in_progress, completed, blocked.
    """
    todos = _load()

    if status:
        filtered = [t for t in todos if t.get("status") == status]
    else:
        filtered = todos

    # summary counts
    counts = {
        "pending": sum(1 for t in todos if t["status"] == "pending"),
        "in_progress": sum(1 for t in todos if t["status"] == "in_progress"),
        "completed": sum(1 for t in todos if t["status"] == "completed"),
        "blocked": sum(1 for t in todos if t["status"] == "blocked"),
    }

    return {"todos": filtered, "counts": counts}


def mark_todo(id: str, status: str, evidence: str = None) -> dict:
    """
    Update a todo item's status.

    Status must be one of: pending, in_progress, completed, blocked.

    For status='completed': evidence is required — must be a verification
    command's exit code or clear proof the task is actually done.
    For status='blocked': evidence should explain what's blocking.
    """
    valid_statuses = {"pending", "in_progress", "completed", "blocked"}
    if status not in valid_statuses:
        return {"error": f"status must be one of {sorted(valid_statuses)}"}

    todos = _load()

    for todo in todos:
        if todo["id"] == id:

            # enforce evidence for completed
            if status == "completed" and not evidence:
                return {
                    "error": (
                        f"cannot mark '{id}' completed without evidence. "
                        "Provide the verification command's exit code or "
                        "clear proof the task is done. "
                        f"Verification method: {todo.get('verification', 'not specified')}"
                    )
                }

            todo["status"] = status
            todo["evidence"] = evidence
            todo["updated_at"] = datetime.now(UTC).isoformat()
            _save(todos)

            return {"updated": todo, "todos": todos}

    return {"error": f"todo with id '{id}' not found"}


def clear_todos() -> dict:
    """Clear all todos — used when starting a fresh task."""
    _save([])
    return {"status": "cleared"}


def all_completed() -> bool:
    """Return True if todo list exists and every item is completed."""
    todos = _load()
    if not todos:
        return False
    return all(t["status"] == "completed" for t in todos)


def has_pending() -> bool:
    """Return True if any todo is pending or in_progress."""
    todos = _load()
    return any(t["status"] in ("pending", "in_progress") for t in todos)


TOOLS_SCHEMA = [
    {
        "type": "function",
        "function": {
            "name": "add_todos",
            "description": (
                "Record your plan as a todo list before starting multi-step work. "
                "Call this FIRST before doing anything else on a complex task. "
                "Each todo needs a title, description, and verification method — "
                "a concrete command or check that proves the item is actually done. "
                "Send the full plan at once, not one item at a time."
            ),
            "parameters": {
                "type": "object",
                "properties": {
                    "items": {
                        "type": "array",
                        "description": "List of todo items to add.",
                        "items": {
                            "type": "object",
                            "properties": {
                                "title": {
                                    "type": "string",
                                    "description": "Short name for this task.",
                                },
                                "description": {
                                    "type": "string",
                                    "description": "What needs to be done.",
                                },
                                "verification": {
                                    "type": "string",
                                    "description": (
                                        "Concrete command or check to confirm done. "
                                        "e.g. 'run pytest tests/test_auth.py and confirm exit code 0'"
                                    ),
                                },
                            },
                            "required": ["title", "description", "verification"],
                        },
                    }
                },
                "required": ["items"],
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "get_todos",
            "description": (
                "Return the current todo list with status counts. "
                "Check this to see what's pending before deciding what to do next."
            ),
            "parameters": {
                "type": "object",
                "properties": {
                    "status": {
                        "type": "string",
                        "enum": ["pending", "in_progress", "completed", "blocked"],
                        "description": "Filter by status. Omit to get all todos.",
                    }
                },
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "mark_todo",
            "description": (
                "Update a todo item's status. "
                "For 'completed': you MUST provide evidence — the exit code from "
                "the verification command, or clear proof the task is done. "
                "Do NOT mark completed just because you think it's done — "
                "run the verification command first and paste its exit code. "
                "For 'blocked': explain what's blocking in evidence."
            ),
            "parameters": {
                "type": "object",
                "properties": {
                    "id": {
                        "type": "string",
                        "description": "The todo item's id.",
                    },
                    "status": {
                        "type": "string",
                        "enum": ["pending", "in_progress", "completed", "blocked"],
                        "description": "New status for this item.",
                    },
                    "evidence": {
                        "type": "string",
                        "description": (
                            "Required for 'completed': paste the verification "
                            "command output or exit code here. "
                            "Required for 'blocked': explain what's blocking."
                        ),
                    },
                },
                "required": ["id", "status"],
            },
        },
    },
]


if __name__ == "__main__":
    # clear first for clean test
    clear_todos()

    print("=== Test 1: add todos ===")
    result = add_todos([
        {
            "title": "Run failing tests",
            "description": "Run pytest to confirm which tests fail",
            "verification": "run pytest and check exit code",
        },
        {
            "title": "Find root cause",
            "description": "grep and read_file to find the bug",
            "verification": "identify file:line of the bug",
        },
        {
            "title": "Fix and verify",
            "description": "edit_file to fix, then re-run pytest",
            "verification": "pytest exit code 0",
        },
    ])
    print(result)

    print("\n=== Test 2: mark first in_progress ===")
    print(mark_todo("todo_1", "in_progress"))

    print("\n=== Test 3: try to complete without evidence (should fail) ===")
    print(mark_todo("todo_1", "completed"))

    print("\n=== Test 4: complete with evidence ===")
    print(mark_todo("todo_1", "completed", evidence="pytest exit code 0"))

    print("\n=== Test 5: get all todos ===")
    print(get_todos())

    print("\n=== Test 6: has_pending ===")
    print("has_pending:", has_pending())