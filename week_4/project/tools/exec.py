import os
import shlex
import subprocess

WORKSPACE_ROOT = os.path.abspath(os.environ.get("WORKSPACE_ROOT", "."))
TIMEOUT_DEFAULT = 10
MAX_OUTPUT_CHARS = 8_000

READ_ONLY_PREFIXES = (
    "grep", "find", "ls", "cat", "head", "tail", "wc",
    "git log", "git diff", "git status", "git blame", "git show",
    "pytest", "python -m pytest", "ruff", "flake8", "mypy",
    "echo", "pwd", "which", "type", "python -c", "pip show", "pip list",
)

DESTRUCTIVE_PATTERNS = (
    "rm ", "mv ", " > ", " >> ", ">", ">>",
    "git commit", "git push", "git checkout --", "git reset",
    "pip install", "npm install", "yarn add",
    "curl ", "wget ", "sudo ", "chmod ", "chown ",
    "mkfifo", "mknod", "dd ", "format",
)


def paths_within_sandbox(command: str, workspace_root: str) -> bool:
    """
    Token-level check: no path-looking argument in command may resolve
    outside workspace_root.
    """
    try:
        tokens = shlex.split(command)
    except ValueError:
        return True  # can't parse, let classify_command handle it

    for token in tokens:
        # looks like a path if it starts with / .. ~ or contains /
        if token.startswith(("/", "..", "~")) or ("/" in token and not token.startswith("-")):
            resolved = os.path.realpath(os.path.join(workspace_root, token))
            workspace_real = os.path.realpath(workspace_root)
            if not resolved.startswith(workspace_real):
                return False
    return True


def classify_command(command: str) -> str:
    """
    Return 'read_only' if command matches a known-safe prefix and no
    destructive pattern. Otherwise return 'ask'.
    """
    cmd = command.strip().lower()

    # check destructive first — takes priority
    for pattern in DESTRUCTIVE_PATTERNS:
        if pattern in cmd:
            return "ask"

    # check read-only prefixes
    for prefix in READ_ONLY_PREFIXES:
        if cmd.startswith(prefix.lower()):
            return "read_only"

    return "ask"


def _execute(command: str, cwd: str, timeout: int) -> dict:
    """Run the command and return structured output."""
    try:
        result = subprocess.run(
            command,
            shell=True,
            cwd=cwd,
            timeout=timeout,
            capture_output=True,
            text=True,
        )

        stdout = result.stdout
        stderr = result.stderr
        truncated = False

        if len(stdout) > MAX_OUTPUT_CHARS:
            stdout = stdout[:MAX_OUTPUT_CHARS]
            truncated = True

        return {
            "stdout": stdout,
            "stderr": stderr[:MAX_OUTPUT_CHARS],
            "exit_code": result.returncode,
            "truncated": truncated,
        }

    except subprocess.TimeoutExpired:
        return {
            "stdout": "",
            "stderr": f"Command timed out after {timeout} seconds.",
            "exit_code": -1,
            "truncated": False,
        }
    except Exception as e:
        return {
            "stdout": "",
            "stderr": str(e),
            "exit_code": -1,
            "truncated": False,
        }


def run_command(command: str, cwd: str = WORKSPACE_ROOT, timeout: int = TIMEOUT_DEFAULT) -> dict:
    """
    Run a shell command sandboxed to cwd.
    - Read-only commands run immediately.
    - Destructive or unclassified commands pause for y/n approval.
    """
    # sandbox check
    if not paths_within_sandbox(command, cwd):
        return {
            "error": "blocked: command references a path outside the workspace."
        }

    classification = classify_command(command)

    if classification == "read_only":
        return _execute(command, cwd, timeout)

    # ask for approval
    print("\n" + "="*60)
    print("WARNING: the agent wants to run a command that may")
    print("write, delete, install, or otherwise change the system:")
    print(f"\n    {command}\n")
    print("="*60)

    try:
        answer = input("Allow this command? [y/N]: ").strip().lower()
    except (EOFError, KeyboardInterrupt):
        answer = "n"

    if answer != "y":
        return {
            "error": "blocked: user did not approve this command. "
                     "Try a read-only alternative or explain why this is needed."
        }

    return _execute(command, cwd, timeout)


TOOLS_SCHEMA = [
    {
        "type": "function",
        "function": {
            "name": "run_command",
            "description": (
                "Run a shell command in the workspace and return its output. "
                "Use this to search (grep/find), inspect history (git log/diff), "
                "run tests (pytest), or run linters. "
                "Read-only commands (grep, find, ls, git log, pytest) run immediately. "
                "Anything that writes, deletes, or installs will pause and ask the "
                "human operator for y/n approval before running — expect that pause, "
                "it is not a failure, wait for the result. "
                "Always check exit_code to confirm success — do not assume a command "
                "worked just because it produced output."
            ),
            "parameters": {
                "type": "object",
                "properties": {
                    "command": {
                        "type": "string",
                        "description": "The shell command to run.",
                    },
                    "timeout": {
                        "type": "integer",
                        "description": f"Seconds before the command is killed. Default {TIMEOUT_DEFAULT}.",
                    },
                },
                "required": ["command"],
            },
        },
    }
]


if __name__ == "__main__":
    print("=== Test 1: Read-only command (runs immediately) ===")
    print(run_command("git log --oneline -5"))

    print("\n=== Test 2: Destructive command (asks for approval) ===")
    print(run_command("rm -rf /tmp/does-not-exist-example"))