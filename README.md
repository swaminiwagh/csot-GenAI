# Week 1 - LLM APIs, API-Key Safety & Conversation State

## Overview

This project is a terminal-based chatbot built using OpenRouter and the OpenAI Python SDK.

The chatbot demonstrates:

- Secure API key management using `.env`
- Multi-turn conversations
- Conversation history management
- Stateless API behaviour
- Token usage tracking
- Model selection
- Object-Oriented Programming using a ChatAgent class

---

## Features

### Multi-turn Chat

The chatbot remembers previous messages by maintaining a conversation history.

### Model Selection

Choose between:

1. Gemma 31B
2. openai
3. deepseek

### Commands

#### Exit

```text
exit
```

or

```text
quit
```

Ends the conversation.

#### Reset

```text
/reset
```

Clears conversation history.

#### Token Usage

```text
/tokens
```

Displays prompt tokens, completion tokens and total tokens from the last API call.

---

## Installation

Install dependencies:

```bash
pip install -r requirements.txt
```

Create a `.env` file:

```env
OPENROUTER_API_KEY=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
```

Run the chatbot:

```bash
python chatbot.py
```

---

## Rolling Buffer

The chatbot keeps only the latest 5 conversation turns.

Older messages are removed automatically to prevent the conversation history from growing indefinitely.

---

## Learning Outcomes

Through this project I learned:

- How LLM APIs work
- API key security best practices
- Role-based chat templates
- Maintaining conversation state
- Token usage tracking
- Basic OOP design for AI applications