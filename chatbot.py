import os
from openai import OpenAI
from dotenv import load_dotenv

load_dotenv()


class ChatAgent:
    def __init__(
        self,
        model="deepseek/deepseek-v4-flash:free",
        max_turns=5,
        system_prompt="You are a helpful assistant."
    ):
        self.model = model
        self.max_turns = max_turns
        self.system_prompt = system_prompt

        self.client = OpenAI(
            base_url="https://openrouter.ai/api/v1",
            api_key=os.environ["OPENROUTER_API_KEY"],
        )

        self.messages = [
            {
                "role": "system",
                "content": self.system_prompt
            }
        ]

        self.last_usage = None

    def call_model(self):
        try:
            response = self.client.chat.completions.create(
                model=self.model,
                messages=self.messages
            )

            self.last_usage = response.usage

            assistant_reply = response.choices[0].message.content

            return assistant_reply

        except Exception as e:
            print(f"\nAPI Error: {e}\n")
            return "Unable to generate a response."

    def add_user_message(self, message):
        self.messages.append(
            {
                "role": "user",
                "content": message
            }
        )

    def add_assistant_message(self, message):
        self.messages.append(
            {
                "role": "assistant",
                "content": message
            }
        )

    def reset(self):
        self.messages = [
            {
                "role": "system",
                "content": self.system_prompt
            }
        ]

    def trim_history(self):
        max_messages = 1 + (self.max_turns * 2)

        while len(self.messages) > max_messages:
            del self.messages[1:3]

    def show_tokens(self):
        if self.last_usage is None:
            print("No API call made yet.")
            return

        print("\nToken Usage")
        print("---------------------")
        print(f"Prompt Tokens: {self.last_usage.prompt_tokens}")
        print(f"Completion Tokens: {self.last_usage.completion_tokens}")
        print(f"Total Tokens: {self.last_usage.total_tokens}")
        print()

    def chat(self):
        print("\nChat started!")
        print("Commands:")
        print("  /reset  -> clear history")
        print("  /tokens -> show token usage")
        print("  exit    -> quit\n")

        while True:
            user_input = input("You: ")

            if user_input.lower() in ["exit", "quit"]:
                print("Goodbye!")
                break

            if user_input == "/reset":
                self.reset()
                print("Conversation history cleared.\n")
                continue

            if user_input == "/tokens":
                self.show_tokens()
                continue

            self.add_user_message(user_input)

            reply = self.call_model()

            self.add_assistant_message(reply)

            self.trim_history()

            print(f"\nAssistant: {reply}\n")


def choose_model():
    models = {
        "1": "google/gemma-4-31b-it:free",
        "2": "openai/gpt-oss-120b:free",
        "3": "deepseek/deepseek-v4-flash"
    }

    print("Choose a model:")
    print("1. Gemma 31B")
    print("2. openai")
    print("3. deepseek")

    choice = input("\nEnter choice (1-3): ")

    return models.get(choice, models["1"])


if __name__ == "__main__":
    selected_model = choose_model()

    agent = ChatAgent(
        model=selected_model,
        max_turns=5
    )

    agent.chat()