## Git Workflow
- Never commit directly to main
- Create feature branches for each task
- Open PRs using `gh pr create` for review
- Use conventional commit messages (feat:, fix:, docs:, etc.)
- Commit with a descriptive message

## Unit Tests
- write unit tests using PyTest

## Package Management
- use uv to install and maintain packages
- always use the virtual environment - never install packages globally

## Coding Conventions
- Use async/await for all HTTP requests
- Cache SEC responses to avoid repeated fetches
- Type hints on all Python functions
- Use docstrings on all Python functions
- Use PEP 8 Python standards