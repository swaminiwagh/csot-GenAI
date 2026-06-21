from textual.app import App, ComposeResult
from textual.widgets import Header, Footer, Input, RichLog
from textual.binding import Binding
from build2_agent_class import Agent


class TUIAgent(Agent):

    def _emit(self, event, **kwargs):
        if event == "tool_call":
            # Will be overridden by the App to log to screen
            if hasattr(self, "_log_callback"):
                self._log_callback(f"[tool] {kwargs['name']}")


class ResearchDeskApp(App):

    TITLE = "Research Desk"
    BINDINGS = [
        Binding("ctrl+q", "quit", "Quit"),
    ]

    def compose(self) -> ComposeResult:
        yield Header()
        yield RichLog(id="log", wrap=True, highlight=True, markup=True)
        yield Input(placeholder="Ask a research question...")
        yield Footer()

    def on_mount(self):
        self.agent = TUIAgent()
        self.agent._log_callback = self.log_message
        log = self.query_one("#log", RichLog)
        log.write(f"[bold green]Research Desk[/bold green] — Session: {self.agent.session_id}")
        log.write("Type your question and press Enter. Ctrl+Q to quit.\n")

    def log_message(self, text):
        log = self.query_one("#log", RichLog)
        log.write(f"[dim]{text}[/dim]")

    def on_input_submitted(self, event: Input.Submitted):
        user_text = event.value.strip()
        if not user_text:
            return

        log = self.query_one("#log", RichLog)
        inp = self.query_one(Input)
        inp.value = ""

        log.write(f"\n[bold cyan]You:[/bold cyan] {user_text}")

        # Run in a worker so UI doesn't freeze
        self.run_worker(self._respond(user_text), exclusive=True)

    async def _respond(self, user_text):
        log = self.query_one("#log", RichLog)
        try:
            response = self.agent.chat(user_text)
            log.write(f"\n[bold green]Assistant:[/bold green] {response}\n")
        except Exception as e:
            log.write(f"\n[bold red]Error:[/bold red] {e}\n")


def main():
    app = ResearchDeskApp()
    app.run()


if __name__ == "__main__":
    main()