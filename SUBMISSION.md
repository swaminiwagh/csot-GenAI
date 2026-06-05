# Week 1 Submission

## What I Built

I implemented a terminal-based chatbot using OpenRouter and the OpenAI Python SDK.

The chatbot supports:

* Multi-turn conversations
* Model selection before starting the chat
* Conversation history using role-based messages
* Token usage tracking using `/tokens`
* History reset using `/reset`
* Conversation compaction using `/compact`
* API key loading from environment variables using python-dotenv

## Implementation Details

I created a ChatAgent class that manages the conversation history and API calls.

The conversation is stored as a list of messages containing system, user, and assistant roles. The full history is sent with every API request because the API is stateless.

I also implemented a rolling memory buffer to limit the amount of conversation history stored.

## Challenges Faced

Initially I faced issues with:

* Python and pip setup
* Invalid or unavailable model IDs on OpenRouter
* Understanding how environment variables work
* Handling API errors gracefully

I learned how API keys should be stored securely and why conversation history needs to be manually maintained.

## Key Learnings

* LLM APIs are stateless.
* Conversation memory comes from the messages list.
* API keys should never be hardcoded.
* Token usage is important for cost and context management.
* System, user, and assistant roles affect model behaviour.
