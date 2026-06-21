import os
import sys
import json

from dotenv import load_dotenv
from openai import OpenAI

from build1_sessions import (
    create_session,
    load_session,
    save_session,
    build_system_prompt,
)

from tools.web import web_search, web_fetch
from tools.files import (
    read_file,
    write_file,
    edit_file,
    list_files,
)
from tools.papers import (
    paper_search,
    read_paper,
)

load_dotenv()

client = OpenAI(
    base_url="https://openrouter.ai/api/v1",
    api_key=os.environ["OPENROUTER_API_KEY"],
)

MODEL = "deepseek/deepseek-chat"


TOOLS = {
    "web_search": web_search,
    "web_fetch": web_fetch,
    "paper_search": paper_search,
    "read_paper": read_paper,
    "read_file": read_file,
    "write_file": write_file,
    "edit_file": edit_file,
    "list_files": list_files,
}

TOOLS_SCHEMA = [
    {
        "type": "function",
        "function": {
            "name": "web_search",
            "description": "Search the web",
            "parameters": {
                "type": "object",
                "properties": {
                    "query": {"type": "string"}
                },
                "required": ["query"]
            }
        }
    },
    {
        "type": "function",
        "function": {
            "name": "web_fetch",
            "description": "Fetch webpage content",
            "parameters": {
                "type": "object",
                "properties": {
                    "url": {"type": "string"}
                },
                "required": ["url"]
            }
        }
    },
    {
        "type": "function",
        "function": {
            "name": "paper_search",
            "description": "Search academic papers",
            "parameters": {
                "type": "object",
                "properties": {
                    "query": {"type": "string"},
                    "limit": {"type": "integer"}
                },
                "required": ["query"]
            }
        }
    },
    {
        "type": "function",
        "function": {
            "name": "read_paper",
            "description": "Read paper contents",
            "parameters": {
                "type": "object",
                "properties": {
                    "arxiv_id": {"type": "string"}
                },
                "required": ["arxiv_id"]
            }
        }
    },
    {
        "type": "function",
        "function": {
            "name": "read_file",
            "description": "Read file",
            "parameters": {
                "type": "object",
                "properties": {
                    "path": {"type": "string"},
                    "start_line": {"type": "integer"},
                    "read_lines": {"type": "integer"}
                },
                "required": ["path"]
            }
        }
    },
    {
        "type": "function",
        "function": {
            "name": "write_file",
            "description": "Write file",
            "parameters": {
                "type": "object",
                "properties": {
                    "path": {"type": "string"},
                    "content": {"type": "string"}
                },
                "required": ["path", "content"]
            }
        }
    },
    {
        "type": "function",
        "function": {
            "name": "edit_file",
            "description": "Edit file",
            "parameters": {
                "type": "object",
                "properties": {
                    "path": {"type": "string"},
                    "operation": {"type": "string"},
                    "start_line": {"type": "integer"},
                    "end_line": {"type": "integer"},
                    "content": {"type": "string"}
                },
                "required": ["path", "operation", "start_line"]
            }
        }
    },
    {
        "type": "function",
        "function": {
            "name": "list_files",
            "description": "List files",
            "parameters": {
                "type": "object",
                "properties": {
                    "path": {"type": "string"},
                    "pattern": {"type": "string"}
                }
            }
        }
    }
]

class Agent:
    def __init__(self, session_id=None):
        self.session_id = session_id or create_session()

        loaded = load_session(self.session_id)

        if loaded:
            self.messages = loaded["messages"]
        else:
            self.messages = [
                {
                    "role": "system",
                    "content": build_system_prompt(),
                }
            ]

    def _emit(self, event, **kwargs):
        """
        Hook for subclasses.
        """
        pass

    def dispatch(self, tool_name, arguments):
        """
        Execute one tool.
        """

        print(f"\n[TOOL CALLED] {tool_name}")
        print(f"ARGS: {arguments}")

        if tool_name not in TOOLS:
            error = {
                "error": f"Unknown tool {tool_name}"
            }

            print(f"RESULT: {error}\n")
            return error

        self._emit(
            "tool_call",
            name=tool_name,
        )

        try:
            result = TOOLS[tool_name](**arguments)

            print(f"RESULT: {result}\n")

            return result

        except Exception as e:
            error = {
                "error": str(e)
            }

            print(f"ERROR: {error}\n")

            return error

    def _run_loop(self):
        MAX_ITERATIONS = 10
        iterations = 0

        while iterations < MAX_ITERATIONS:
            iterations += 1

            response = client.chat.completions.create(
                model=MODEL,
                messages=self.messages,
                tools=TOOLS_SCHEMA,
                tool_choice="auto",
            )

            message = response.choices[0].message
            finish_reason = response.choices[0].finish_reason

            # No tool calls — final answer
            if finish_reason == "stop" or not message.tool_calls:
                final_text = message.content
                if not final_text:
                    # Model returned empty - ask it to summarize what it found
                    self.messages.append({
                        "role": "user", 
                        "content": "Please summarize what you found and give me your best answer."
                    })
                    retry = client.chat.completions.create(
                        model=MODEL,
                        messages=self.messages,
                    )
                    final_text = retry.choices[0].message.content or "I was unable to find results."

                self.messages.append({
                    "role": "assistant",
                    "content": final_text,
                })

                return final_text

            # Append assistant message with tool calls
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

            # Execute each tool and append results
            for tc in message.tool_calls:
                tool_name = tc.function.name.strip()
                arguments = json.loads(tc.function.arguments)
                result = self.dispatch(tool_name, arguments)

                self.messages.append({
                    "role": "tool",
                    "tool_call_id": tc.id,
                    "content": json.dumps(result),
                })

        return "Max iterations reached."

    def chat(self, user_message):

        self.messages.append(
            {
                "role": "user",
                "content": user_message,
            }
        )

        answer = self._run_loop()

        save_session(
            self.session_id,
            self.messages,
        )

        return answer

    def run_once(self, prompt):
        return self.chat(prompt)


class REPLAgent(Agent):

    def run(self):

        print(f"Research Desk [{self.session_id}]")

        while True:

            try:
                user = input("> ").strip()
            except (EOFError, KeyboardInterrupt):
                print()
                break

            if user in (
                "/quit",
                "/exit",
            ):
                break

            print(self.chat(user))
            print()

    def _emit(self, event, **kwargs):

        if event == "tool_call":
            print(
                f"[tool] {kwargs['name']}",
                file=sys.stderr,
            )


def main():

    agent = REPLAgent()

    if len(sys.argv) > 1:
        print(
            agent.run_once(
                " ".join(sys.argv[1:])
            )
        )

    else:
        agent.run()


if __name__ == "__main__":
    main()