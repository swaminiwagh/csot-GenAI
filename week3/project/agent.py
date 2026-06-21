import sys
from build2_agent_class import REPLAgent


def main():
    if "--tui" in sys.argv:
        from tui import ResearchDeskApp
        app = ResearchDeskApp()
        app.run()

    elif len(sys.argv) > 1:
        args = [a for a in sys.argv[1:] if not a.startswith("--")]
        # Force the agent to use tools, not just describe what it will do
        prompt = " ".join(args) + " (use your tools to answer this now, do not just describe what you will do)"
        agent = REPLAgent()
        print(agent.run_once(prompt))

    else:
        agent = REPLAgent()
        agent.run()


if __name__ == "__main__":
    main()