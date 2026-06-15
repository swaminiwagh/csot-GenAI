# Week 2: Research Agent with Tools + TUI

## Overview

This project builds a **full research agent** inspired by Perplexity.ai. It can search the web, fetch and read full web pages, and provide well-sourced answers using an agent loop (ReAct pattern).

The agent runs inside a beautiful **Textual TUI** (Terminal User Interface) with split panels for chat and tool activity.
 
## Features

- **Web Search** using Serper.dev
- **Web Fetch** with smart cleaning (`trafilatura` + `markdownify`) and `llms.txt` support
- **Agent Loop** with up to 12 iterations (tool calling via OpenAI SDK format)
- **Full-screen TUI** with real-time tool logging
- **Keyboard Shortcuts**:
  - `Ctrl + L` → Clear display
  - `Ctrl + K` → Clear conversation history
  - `Ctrl + Q` → Quit
  - `Ctrl + S` → Save conversation to `research_notes.md`

## Learning Outcomes

- Implemented custom tool calling with the OpenAI SDK
- Built a proper agent loop with iteration limit
- Created a responsive Terminal UI using Textual
- Handled web content cleaning and token management
- Understood ReAct-style reasoning + acting

---

## How to Run

```bash
cd week_2/project
python agent.py
