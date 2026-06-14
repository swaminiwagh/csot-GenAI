# ResearchBot Agent

Main entry point for Week 2 project.

This file contains:
- Tool definitions (`web_search`, `web_fetch`)
- Agent loop implementation
- Textual TUI with split panels (Chat + Tool Log)
- Keyboard bindings and note saving
 
## Architecture

- **Tools**: Exposed via OpenAI function calling format
- **Agent Loop**: Continues calling tools until the model gives a final answer
- **UI**: Built with Textual library for a modern terminal experience

## Testing & Troubleshooting

During development, I created a small `test.py` script to verify API connectivity and diagnose OpenRouter-related issues independently of the main TUI application.

This helped identify:
- API key authentication issues (401 errors)
- Model availability errors (404 errors)
- Environment variable loading problems
- OpenRouter connectivity issues

Once the API and model configuration were verified, the main `agent.py` application ran successfully.

Run with: `python agent.py`