import os
import json
from typing import Dict, List

from dotenv import load_dotenv
from openai import OpenAI
import requests
from markdownify import markdownify
import trafilatura
from textual.app import App, ComposeResult
from textual.binding import Binding
from textual.widgets import Header, Footer, Input, RichLog
from textual.containers import Horizontal

load_dotenv()
print("ENV LOADED")
print("KEY =", os.getenv("OPENROUTER_API_KEY"))
print("SERPER =", os.getenv("SERPER_API_KEY"))

client = OpenAI(
    base_url="https://openrouter.ai/api/v1",
    api_key=os.environ["OPENROUTER_API_KEY"],
)

MODEL = "deepseek/deepseek-v4-flash"
SERPER_API_KEY = os.environ.get("SERPER_API_KEY")

MAX_ITERATIONS = 12
MAX_FETCH_CHARS = 8000

def web_search(query: str, num_results: int = 5) -> List[Dict]:
    if not SERPER_API_KEY:
        return [{"error": "SERPER_API_KEY not set"}]
    try:
        response = requests.post(
            "https://google.serper.dev/search",
            headers={"X-API-KEY": SERPER_API_KEY, "Content-Type": "application/json"},
            json={"q": query, "num": num_results},
            timeout=15,
        )
        response.raise_for_status()
        data = response.json()
        results = []
        for item in data.get("organic", [])[:num_results]:
            results.append({
                "title": item.get("title", ""),
                "link": item.get("link", ""),
                "snippet": item.get("snippet", ""),
            })
        return results
    except Exception as e:
        return [{"error": str(e)}]


def web_fetch(url: str) -> str:
    try:
        headers = {"User-Agent": "Mozilla/5.0 (compatible; ResearchBot/1.0)"}
        response = requests.get(url, headers=headers, timeout=15, allow_redirects=True)
        response.raise_for_status()
        
        from urllib.parse import urlparse
        base = f"{urlparse(url).scheme}://{urlparse(url).netloc}"
        try:
            llms_resp = requests.get(f"{base}/llms.txt", timeout=5, headers=headers)
            if llms_resp.status_code == 200:
                return f"[llms.txt from {base}]\n\n{llms_resp.text}\n\n---\nOriginal: {url}"
        except:
            pass
        
        html = response.text
        text = trafilatura.extract(html, include_comments=False, include_tables=True) or ""
        if not text:
            md = markdownify(html, heading_style="ATX", strip=["script", "style", "nav", "footer"])
            text = md
        if len(text) > MAX_FETCH_CHARS:
            text = text[:MAX_FETCH_CHARS] + "\n\n[...truncated]"
        return text
    except Exception as e:
        return f"Error fetching {url}: {str(e)}"


TOOLS = [
    {
        "type": "function",
        "function": {
            "name": "web_search",
            "description": "Search the web for current information.",
            "parameters": {
                "type": "object",
                "properties": {
                    "query": {"type": "string", "description": "Search query"},
                    "num_results": {"type": "integer", "default": 5}
                },
                "required": ["query"]
            }
        }
    },
    {
        "type": "function",
        "function": {
            "name": "web_fetch",
            "description": "Fetch full content of a webpage URL.",
            "parameters": {
                "type": "object",
                "properties": {
                    "url": {"type": "string", "description": "Full URL"}
                },
                "required": ["url"]
            }
        }
    },
]

def dispatch_tool(tool_call) -> str:
    try:
        name = tool_call.function.name
        args = json.loads(tool_call.function.arguments)
        if name == "web_search":
            return json.dumps(web_search(**args), ensure_ascii=False, default=str)
        elif name == "web_fetch":
            return json.dumps({"content": web_fetch(**args)}, ensure_ascii=False, default=str)
        return json.dumps({"error": f"Unknown tool: {name}"})
    except Exception as e:
        return json.dumps({"error": str(e)})


def run_agent_loop(user_message: str, messages: List[Dict] = None) -> tuple[str, List[Dict]]:
    if messages is None:
        messages = [
            {"role": "system", "content": "You are a helpful research assistant. Use tools to get accurate info."},
            {"role": "user", "content": user_message},
        ]
    else:
        messages = messages.copy()
        messages.append({"role": "user", "content": user_message})

    for _ in range(MAX_ITERATIONS):
        response = client.chat.completions.create(
            model=MODEL,
            messages=messages,
            tools=TOOLS,
        )
        message = response.choices[0].message
        finish_reason = response.choices[0].finish_reason

        messages.append(message.model_dump() if hasattr(message, 'model_dump') else dict(message))

        if finish_reason == "tool_calls" and message.tool_calls:
            for tool_call in message.tool_calls:
                result = dispatch_tool(tool_call)
                messages.append({
                    "role": "tool",
                    "tool_call_id": tool_call.id,
                    "content": result,
                })
            continue
        else:
            return message.content or "No response generated.", messages

    return "[Max iterations reached]", messages


class ResearchAgentApp(App):
    TITLE = "ResearchBot - Week 2"
    CSS = """
    Screen { layout: vertical; }
    Horizontal { height: 1fr; }
    #chat-log { width: 70%; border: solid $primary; padding: 1; }
    #tool-log { width: 30%; border: solid $warning; padding: 1; }
    Input { dock: bottom; height: 3; }
    """

    BINDINGS = [
        Binding("ctrl+l", "clear_display", "Clear Display"),
        Binding("ctrl+k", "clear_history", "Clear History"),
        Binding("ctrl+q", "quit", "Quit"),
        Binding("ctrl+s", "save_notes", "Save Notes"),
    ]

    def __init__(self):
        super().__init__()
        self.messages: List[Dict] = [
            {"role": "system", "content": "You are a helpful research assistant."}
        ]

    def compose(self) -> ComposeResult:
        yield Header(show_clock=True)
        with Horizontal():
            yield RichLog(id="chat-log", wrap=True, markup=True, highlight=True)
            yield RichLog(id="tool-log", wrap=True, markup=True)
        yield Input(placeholder="Ask a research question...")
        yield Footer()

    def on_mount(self) -> None:
        self.query_one("#chat-log", RichLog).write("[bold green]Ready! Type your question.[/bold green]\n")
        self.query_one(Input).focus()

    def on_input_submitted(self, event: Input.Submitted) -> None:
        user_text = event.value.strip()
        if not user_text: return
        event.input.clear()

        chat = self.query_one("#chat-log", RichLog)
        chat.write(f"[bold cyan]You:[/bold cyan] {user_text}\n")

        self.run_worker(self._process_query(user_text), thread=True)

    async def _process_query(self, user_text: str):
        chat = self.query_one("#chat-log", RichLog)
        tool = self.query_one("#tool-log", RichLog)
        try:
            self.call_from_thread(tool.write, "[bold yellow]Thinking...[/bold yellow]\n")
            answer, self.messages = run_agent_loop(user_text, self.messages)
            self.call_from_thread(chat.write, f"[bold green]ResearchBot:[/bold green] {answer}\n\n")
        except Exception as e:
            self.call_from_thread(chat.write, f"[bold red]Error: {e}[/bold red]\n")

    def action_clear_display(self):
        self.query_one("#chat-log", RichLog).clear()
        self.query_one("#tool-log", RichLog).clear()

    def action_clear_history(self):
        self.messages = [{"role": "system", "content": "You are a helpful research assistant."}]
        self.query_one("#chat-log", RichLog).clear()
        self.query_one("#tool-log", RichLog).clear()

    def action_save_notes(self):
        try:
            with open("research_notes.md", "w", encoding="utf-8") as f:
                f.write("# Research Notes\n\n")
                for m in self.messages:
                    if m.get("role") == "user":
                        f.write(f"**You:** {m.get('content')}\n\n")
                    elif m.get("role") == "assistant":
                        f.write(f"**Bot:** {m.get('content')}\n\n")
            self.call_from_thread(self.query_one("#chat-log", RichLog).write, "[green]Saved to research_notes.md[/green]\n")
        except:
            pass


if __name__ == "__main__":
    ResearchAgentApp().run() 