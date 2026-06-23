# Code Scout Rules

## Workflow — ALWAYS follow this order
1. Call `add_todos` FIRST with your full plan before doing anything else
2. Use `grep` to find the relevant file and line BEFORE running tests
3. Use `read_file` to read the exact lines around the match
4. Use `edit_file` to fix the issue (requires human approval)
5. Run `python -m pytest tests/test_helpers.py` to verify the fix
6. Only mark a todo `completed` after pytest exits with code 0

## Tools
- Use `grep` to search — do NOT run tests repeatedly if tests keep failing
- Use `read_file` once you know which file and line to look at
- Use `edit_file` for precise fixes — prefer over run_command for edits
- Use `run_command` for git history, tests, and broad search
- Read-only commands run immediately; destructive commands pause for y/n

## Critical rules
- If pytest keeps failing, STOP running it and READ the source file instead
- NEVER run the same command more than twice in a row
- Search with grep FIRST, then read the file, then fix, then verify
- A todo is NOT complete until pytest exit code is 0

## Citations
- Always cite file:line for any claim about code