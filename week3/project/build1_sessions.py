import os
import json
import uuid
from datetime import datetime, UTC

SESSIONS_DIR = ".agent/sessions"

BASE_PROMPT = "You are Research Desk, a helpful research agent."


def create_session():
    """Create a new session ID."""
    os.makedirs(SESSIONS_DIR, exist_ok=True)
    return uuid.uuid4().hex[:8]


def save_session(session_id, messages, title="Untitled"):
    """Save a session to disk."""
    os.makedirs(SESSIONS_DIR, exist_ok=True)

    path = os.path.join(SESSIONS_DIR, f"{session_id}.json")

    # Preserve created_at if updating an existing session
    created_at = datetime.now(UTC).isoformat()
    if os.path.exists(path):
        try:
            with open(path, "r", encoding="utf-8") as f:
                existing = json.load(f)
                created_at = existing.get("created_at", created_at)
        except Exception:
            pass

    data = {
        "id": session_id,
        "title": title,
        "created_at": created_at,
        "updated_at": datetime.now(UTC).isoformat(),
        "messages": messages,
    }

    with open(path, "w", encoding="utf-8") as f:
        json.dump(data, f, indent=2)


def load_session(session_id):
    """Load a session from disk."""
    path = os.path.join(SESSIONS_DIR, f"{session_id}.json")

    if not os.path.exists(path):
        return None

    with open(path, "r", encoding="utf-8") as f:
        return json.load(f)


def list_sessions():
    """Return all saved sessions sorted by most recently updated."""
    os.makedirs(SESSIONS_DIR, exist_ok=True)

    sessions = []

    for filename in os.listdir(SESSIONS_DIR):
        if filename.endswith(".json"):
            filepath = os.path.join(SESSIONS_DIR, filename)
            try:
                with open(filepath, "r", encoding="utf-8") as f:
                    sessions.append(json.load(f))
            except Exception:
                pass

    sessions.sort(key=lambda x: x.get("updated_at", ""), reverse=True)
    return sessions


def build_system_prompt():
    """Load base prompt and append AGENTS.md if present."""
    prompt = BASE_PROMPT

    for candidate in ("AGENTS.md", ".agent/AGENTS.md"):
        if os.path.isfile(candidate):
            with open(candidate, "r", encoding="utf-8") as f:
                prompt += "\n\n" + f.read()
            break

    return prompt


if __name__ == "__main__":
    sid = create_session()

    messages = [
        {
            "role": "system",
            "content": build_system_prompt(),
        },
        {
            "role": "user",
            "content": "What is a surface code?",
        },
        {
            "role": "assistant",
            "content": "A surface code is a type of quantum error-correcting code.",
        },
    ]

    save_session(
        session_id=sid,
        messages=messages,
        title="Quantum Error Correction",
    )

    print("Created session:", sid)
    print()

    print("Saved sessions:")
    for session in list_sessions():
        print(
            f"- {session['id']} | {session.get('title', 'Untitled')} | {session.get('updated_at')}"
        )

    print()

    loaded = load_session(sid)
    if loaded:
        print("Loaded session successfully!")
        print("Title:", loaded["title"])
        print("Number of messages:", len(loaded["messages"]))