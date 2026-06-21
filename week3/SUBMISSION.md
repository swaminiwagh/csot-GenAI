# Research Desk — Week 3 Submission

## What I Built

Research Desk is a persistent AI research agent that can search the web,
find and read academic papers, manage notes, and remember past conversations.

## Architecture

The agent is split into a clean class hierarchy:

- `Agent` (in `build2_agent_class.py`) — holds all logic: tool calling loop,
  session save/load, and tool dispatch. No UI code here.
- `REPLAgent(Agent)` — adds a terminal REPL and one-shot CLI on top.
- `TUIAgent(Agent)` (in `tui.py`) — adds a Textual UI, inheriting all agent
  logic from Agent without duplicating it.

## Tools

| Tool | Source |
|------|--------|
| `paper_search` | Hugging Face Papers API |
| `read_paper` | Hugging Face Papers API + markdown |
| `web_search` | Serper API |
| `web_fetch` | trafilatura |
| `read_file` | Local filesystem (sandboxed) |
| `write_file` | Local filesystem (sandboxed) |
| `edit_file` | Line-level editing with preview |
| `list_files` | Local filesystem |

## Sessions

Each conversation gets a unique session ID saved to `.agent/sessions/` as JSON.
On startup the agent loads the most recent session or creates a new one.
AGENTS.md is loaded into the system prompt so the agent always follows project rules.

## How to Run

```bash
# Interactive REPL
python agent.py

# One-shot question
python agent.py "Summarise the LightRAG paper"

# Textual TUI
python agent.py --tui
```

## What I Learned

Building the agent class hierarchy made it clear how to separate brain from UI.
The tool-calling loop (dispatch → tool result → next LLM call) is the core pattern
that makes an agent different from a chatbot. Debugging the HuggingFace API response
structure taught me to always inspect raw API responses before assuming field names.