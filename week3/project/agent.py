import sys
from build2_agent_class import REPLAgent


def main():
    if "--tui" in sys.argv:
        from tui import ResearchDeskApp
        app = ResearchDeskApp()
        app.run()

    elif len(sys.argv) > 1:
        args = [a for a in sys.argv[1:] if not a.startswith("--")]
        agent = REPLAgent()
        from build1_sessions import build_system_prompt
        agent.messages = [{"role": "system", "content": build_system_prompt()}]
        print(agent.run_once(" ".join(args)))

    else:
        agent = REPLAgent()
        agent.run()


if __name__ == "__main__":
    main()