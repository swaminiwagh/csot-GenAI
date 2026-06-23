import os
import sys
import json

from dotenv import load_dotenv
from openai import OpenAI

load_dotenv()

# ── sessions (reused from Week 3) ──────────────────────────────────────────
import uuid
from datetime import datetime, UTC

SESSIONS_DIR = ".agent/sessions"
BASE_PROMPT = "You are Code Scout, an autonomous coding agent."


def create_session():
    os.makedirs(SESSIONS_DIR, exist_ok=True)
    return uuid.uuid4().hex[:8]


def save_session(session_id, messages, title="Untitled"):
    os.makedirs(SESSIONS_DIR, exist_ok=True)
    path = os.path.join(SESSIONS_DIR, f"{session_id}.json")
    created_at = datetime.now(UTC).isoformat()
    if os.path.exists(path):
        try:
            with open(path, "r", encoding="utf-8") as f:
                created_at = json.load(f).get("created_at", created_at)
        except Exception:
            pass
    with open(path, "w", encoding="utf-8") as f:
        json.dump({
            "id": session_id,
            "title": title,
            "created_at": created_at,
            "updated_at": datetime.now(UTC).isoformat(),
            "messages": messages,
        }, f, indent=2)


def load_session(session_id):
    path = os.path.join(SESSIONS_DIR, f"{session_id}.json")
    if not os.path.exists(path):
        return None
    with open(path, "r", encoding="utf-8") as f:
        return json.load(f)


def build_system_prompt():
    prompt = BASE_PROMPT
    for candidate in ("AGENTS.md", ".agent/AGENTS.md"):
        if os.path.isfile(candidate):
            with open(candidate, "r", encoding="utf-8") as f:
                prompt += "\n\n" + f.read()
            break
    return prompt


# ── tools ──────────────────────────────────────────────────────────────────
from tools.exec import run_command, TOOLS_SCHEMA as EXEC_SCHEMA
from tools.search import grep, list_definitions, TOOLS_SCHEMA as SEARCH_SCHEMA
from tools.plan import (
    add_todos, get_todos, mark_todo, clear_todos,
    has_pending, all_completed,
    TOOLS_SCHEMA as PLAN_SCHEMA,
)
from tools.files import (
    read_file, write_file, edit_file, list_files,
    TOOLS_SCHEMA as FILES_SCHEMA,
)

TOOLS = {
    "run_command": run_command,
    "grep": grep,
    "list_definitions": list_definitions,
    "add_todos": add_todos,
    "get_todos": get_todos,
    "mark_todo": mark_todo,
    "read_file": read_file,
    "write_file": write_file,
    "edit_file": edit_file,
    "list_files": list_files,
}

TOOLS_SCHEMA = (
    EXEC_SCHEMA
    + SEARCH_SCHEMA
    + PLAN_SCHEMA
    + FILES_SCHEMA
)

# ── model ──────────────────────────────────────────────────────────────────
client = OpenAI(
    base_url="https://openrouter.ai/api/v1",
    api_key=os.environ["OPENROUTER_API_KEY"],
)
MODEL = "deepseek/deepseek-chat"
MAX_ITERATIONS = 30


# ── Agent ──────────────────────────────────────────────────────────────────
class Agent:
    def __init__(self, session_id=None):
        self.session_id = session_id or create_session()
        loaded = load_session(self.session_id)
        if loaded:
            self.messages = loaded["messages"]
        else:
            self.messages = [
                {"role": "system", "content": build_system_prompt()}
            ]

    def _emit(self, event, **kwargs):
        pass

    def dispatch(self, tool_name, arguments):
        tool_name = tool_name.strip()
        print(f"\n[TOOL] {tool_name}")
        print(f"  args: {json.dumps(arguments, indent=2)[:300]}")

        if tool_name not in TOOLS:
            result = {"error": f"unknown tool: {tool_name}", "suggestion": "Available tools: " + ", ".join(TOOLS.keys())}
            print(f"  result: {result}")
            return result

        self._emit("tool_call", name=tool_name)

        try:
            result = TOOLS[tool_name](**arguments)
            # truncate long results for printing
            result_str = json.dumps(result)
            preview = result_str[:500] + "..." if len(result_str) > 500 else result_str
            print(f"  result: {preview}")
            return result
        except Exception as e:
            result = {"error": str(e)}
            print(f"  error: {result}")
            return result

    def _run_loop(self):
        iterations = 0
        last_commands = []  # track recent commands to detect loops

        while iterations < MAX_ITERATIONS:
            iterations += 1

            response = client.chat.completions.create(
                model=MODEL,
                messages=self.messages[-20:],  # only last 20 messages to save tokens
                tools=TOOLS_SCHEMA,
                tool_choice="auto",
                max_tokens=4000,  # limit output tokens
            )

            message = response.choices[0].message
            finish_reason = response.choices[0].finish_reason

            if finish_reason == "stop" or not message.tool_calls:
                final_text = message.content

                if has_pending() and not all_completed():
                    print("\n[loop] todo list has pending items — pushing model to continue")
                    self.messages.append({
                        "role": "assistant",
                        "content": final_text or "",
                    })
                    self.messages.append({
                        "role": "user",
                        "content": (
                            "Your todo list still has pending items. "
                            "Do NOT run the same command again. "
                            "Use grep to find the bug location, then read_file to read it, "
                            "then edit_file to fix it, then run pytest to verify."
                        ),
                    })
                    continue

                if not final_text:
                    retry = client.chat.completions.create(
                        model=MODEL,
                        messages=self.messages + [{
                            "role": "user",
                            "content": "Please summarize what you found and what was done."
                        }],
                    )
                    final_text = retry.choices[0].message.content or "Task complete."

                self.messages.append({
                    "role": "assistant",
                    "content": final_text,
                })
                return final_text

            # tool calls
            self.messages.append({
                "role": "assistant",
                "content": message.content or "",
                "tool_calls": [
                    {
                        "id": tc.id,
                        "type": "function",
                        "function": {
                            "name": tc.function.name,
                            "arguments": tc.function.arguments,
                        },
                    }
                    for tc in message.tool_calls
                ],
            })

            for tc in message.tool_calls:
                tool_name = tc.function.name.strip()

                # detect repeat command loops
                last_commands.append(tool_name)
                if len(last_commands) > 6:
                    last_commands.pop(0)
                if len(last_commands) == 6 and len(set(last_commands)) == 1:
                    self.messages.append({
                        "role": "tool",
                        "tool_call_id": tc.id,
                        "content": json.dumps({
                            "error": f"You have called {tool_name} 6 times in a row. STOP. Use grep to find the bug, read_file to read it, edit_file to fix it."
                        }),
                    })
                    continue

                try:
                    arguments = json.loads(tc.function.arguments)
                except json.JSONDecodeError:
                    self.messages.append({
                        "role": "tool",
                        "tool_call_id": tc.id,
                        "content": json.dumps({"error": "malformed JSON arguments, please retry"}),
                    })
                    continue

                result = self.dispatch(tool_name, arguments)
                self.messages.append({
                    "role": "tool",
                    "tool_call_id": tc.id,
                    "content": json.dumps(result),
                })

        return f"Stopped after {MAX_ITERATIONS} iterations."

    def chat(self, user_message):
        self.messages.append({"role": "user", "content": user_message})
        clear_todos()  # fresh todo list for each new task
        answer = self._run_loop()
        save_session(self.session_id, self.messages)
        return answer

    def run_once(self, prompt):
        return self.chat(prompt)


# ── REPLAgent ──────────────────────────────────────────────────────────────
class REPLAgent(Agent):

    def run(self):
        print(f"Code Scout [{self.session_id}]")
        print("Type your task and press Enter. /quit to exit.\n")

        while True:
            try:
                user = input("> ").strip()
            except (EOFError, KeyboardInterrupt):
                print()
                break

            if not user:
                continue

            if user in ("/quit", "/exit"):
                break

            if user == "/todos":
                from tools.plan import get_todos
                todos = get_todos()
                for t in todos["todos"]:
                    print(f"  [{t['status']}] {t['id']}: {t['title']}")
                print(f"  counts: {todos['counts']}")
                continue

            if user == "/clear-todos":
                clear_todos()
                print("  todos cleared")
                continue

            print()
            print(self.chat(user))
            print()

    def _emit(self, event, **kwargs):
        if event == "tool_call":
            print(f"  → {kwargs['name']}", file=sys.stderr)


# ── main ───────────────────────────────────────────────────────────────────
def main():
    # handle --session flag
    session_id = None
    args = sys.argv[1:]

    if "--session" in args:
        idx = args.index("--session")
        if idx + 1 < len(args):
            session_id = args[idx + 1]
            args = args[:idx] + args[idx + 2:]

    agent = REPLAgent(session_id=session_id)

    if args:
        # one-shot CLI
        prompt = " ".join(a for a in args if not a.startswith("--"))
        agent.messages = [{"role": "system", "content": build_system_prompt()}]
        print(agent.run_once(prompt))
    else:
        agent.run()


if __name__ == "__main__":
    main()