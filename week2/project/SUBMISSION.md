# Week 2 Submission

## What I Built

I built a **research agent** with a full-screen Textual TUI that can search the web, read full articles, and synthesize answers — similar to Perplexity.ai.

The agent uses: 
- `web_search` tool (via Serper)
- `web_fetch` tool (with clean text extraction using trafilatura + markdownify)
- A proper **agent loop** that keeps calling tools until it has enough information
- Split-panel terminal interface showing both conversation and tool activity

## Implementation Details

- Used native OpenAI SDK tool calling (`tools=` parameter and `tool_calls`)
- Implemented `dispatch_tool()` to safely execute functions
- Added `llms.txt` support for better website understanding
- Built the TUI with `RichLog` panels, background workers (so UI doesn't freeze), and multiple keyboard shortcuts
- Conversation history is maintained with proper role handling

## Challenges Faced

1. Making the TUI responsive during API calls → solved using `run_worker(thread=True)` and `call_from_thread()`
2. Cleaning web content (HTML is very noisy) → used `trafilatura` as primary extractor
3. Preventing infinite loops → added `MAX_ITERATIONS = 12`
4. Handling tool errors gracefully so the model can recover

## Key Learnings

- The agent loop (ReAct pattern) is extremely powerful when combined with good tool descriptions
- JSON Schema in tool definitions makes tool calling much more reliable
- Textual makes building professional terminal apps surprisingly easy
- Web content cleaning is one of the most important parts of building useful web agents
- Proper error handling in tools helps the model self-correct

## What Surprised Me

The model became significantly better at research once I gave it both search + fetch tools and let it run in a loop. It started chaining searches naturally (search → read promising link → search again if needed).

## Future Improvements (if more time)

- Add streaming responses (token by token)
- Implement a `save_research_note` tool
- Add memory / note-taking persistence across sessions
- Support multiple tool calls in parallel

Overall, this was a big step up from Week 1. I now understand how production research agents work under the hood.