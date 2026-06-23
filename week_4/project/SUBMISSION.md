# Code Scout — Week 4 Submission

## What I Built

Code Scout is an autonomous CLI coding agent that investigates and fixes bugs in real, unfamiliar codebases. It searches through source files, reads and edits code, executes commands, and verifies its own fixes by rerunning tests. Apart from actions flagged by the safety gate as potentially destructive, the agent operates autonomously without requiring human intervention.

## Target Repository

I evaluated the agent on **Flask**, a well-known Python web framework with a substantial real-world codebase and a test suite containing over 400 tests.

I chose Flask because it is large enough that reading the entire repository is impractical. The agent has to search intelligently before acting, which makes it a good benchmark for testing autonomous investigation. In addition, Flask has a runnable test suite, allowing fixes to be validated objectively instead of relying on the model's own assessment.

## Architecture

The project is organized into the following key components:

* `agent.py` — Core agent loop with todo management, tool dispatch, and session persistence.
* `tools/exec.py` — `run_command` implementation with sandboxing, approval gating, and a read-only allowlist.
* `tools/search.py` — `grep`-based search and `list_definitions` for AST-aware code navigation.
* `tools/plan.py` — Todo management through `add_todos`, `get_todos`, and `mark_todo`, with evidence required before completion.
* `tools/files.py` — `read_file`, `write_file`, `edit_file`, and `list_files`, adapted from the Week 3 implementation.

## Fix-and-Verify Example

To evaluate the agent, I intentionally introduced a bug by renaming `send_file` to `send_fille` in `src/flask/helpers.py`.

I then instructed the agent to locate the typo, restore the correct function name, and verify the fix by rerunning the relevant pytest suite.

The agent:

1. Created a three-step plan using `add_todos`.
2. Used `grep` to locate `send_fille` in `src/flask/helpers.py`.
3. Read the surrounding code before making any changes.
4. Edited the file to restore `send_file`.
5. Reran `python -m pytest tests/test_helpers.py` to verify the result.
6. Recorded the test outcome as evidence before marking the task complete.

Before the fix, the introduced typo caused the relevant helper tests to fail. After restoring the correct function name, the verification run reported **34 passing tests and one remaining unrelated failure**, confirming that the intended bug had been successfully fixed.

## Example of the Approval Gate Preventing an Unnecessary Action

During execution, the agent proposed running `pip install pytest` before executing the tests. Since installing packages modifies the local environment, the approval gate paused execution and requested confirmation instead of running the command automatically.

I declined the request, after which the agent proceeded by invoking `python -m pytest`, which worked correctly without requiring any installation. The approval gate therefore prevented an unnecessary system modification while still allowing the task to complete successfully.

## Example of the Todo Loop Preventing Premature Stopping

The todo-driven loop also improved reliability. After an initial test run reported failures, the model attempted to produce a summary response before completing the remaining planned steps. However, pending todos still existed, so the loop required the agent to continue working instead of stopping early.

The agent subsequently investigated the failure, identified the typo, applied the fix, reran the tests, and only terminated after all planned tasks had been completed and backed by evidence.

## How to Run

```bash
# One-shot task
python agent.py "find the bug in src/flask/helpers.py and fix it"

# Interactive REPL
python agent.py

# Resume a previous session
python agent.py --session <id> "continue the investigation"
```

## What I Learned

Implementing a todo-driven execution loop highlighted the difference between a coding agent and a conventional chatbot. Maintaining an explicit plan prevents the model from stopping after a partial answer and encourages it to carry tasks through to completion.

The approval gate provides an effective safety mechanism by allowing the agent to propose potentially destructive actions while ensuring that a human explicitly authorizes them before execution.

Finally, search-first workflows are essential when working with large repositories. Using tools such as `grep` to narrow the search space is far more efficient than attempting to read files sequentially, enabling the agent to investigate unfamiliar codebases in a scalable manner.
