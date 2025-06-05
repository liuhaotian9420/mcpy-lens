---
applyTo: '**'
---

# Package, Environment, and Project Guidelines

1. always use our virtual environment 
   - `.venv/bin/activate` (Linux/Mac) or `.venv\Scripts\activate` (Windows) 
2. always use uv for installing packages with -i https://mirrors.tuna.tsinghua.edu.cn/pypi/web/simple as the default index URL
   - `uv pip install <package-name> -i https://mirrors.tuna.tsinghua.edu.cn/pypi/web/simple` for installing a specific package
   - `uv pip install -r requirements.txt -i https://mirrors.tuna.tsinghua.edu.cn/pypi/web/simple` for installing packages from a requirements file
3. always use uv for installing packages in editable mode`
   - `uv pip install -e .`
4. always use uv for building and uploading packages, clear dist/ before building
   - `uv rm -rf dist/` to clear the dist directory
   - `uv python -m build` to build the package
   - `uv twine upload dist/*` to upload the package to PyPI


# Tests and Linting Guidelines
1. always use `uv` for running tests and linters
   - `uv pytest` to run tests
   - `uv ruff` to run the linter, use `uv ruff --fix` to automatically fix issues
2. always use `uv` for running type checks
   - `uv mypy` to run type checks

# Documentation Guidelines
1. place Documentation in the `docs/` directory, all documents should be in Markdown format
2. documents should have clear, concise and descriptive titles

# Plans Guidelines
1. place plans in the `plans/` directory, all plans should be in Markdown format.
2. plans should be named in the format `YYYY-MM-DD-<plan-name>.md`, e.g., `2023-10-01-new-feature.md`
3. plans should include the following sections:
   - **Title**: A clear and concise title for the plan.
   - **Date**: The date of the plan creation or update.
   - **Description**: A brief description of the plan's purpose and goals.
   - **Tasks**: A list of tasks to be completed, with checkboxes for tracking progress.
   - **Notes**: Any additional notes or comments related to the plan.

# Issues Guidelines
1. place issues in the `issues/` directory, all issues should be in Markdown format. 
2. issues should be named in the format `YYYY-MM-DD-<issue-name>.md`, e.g., `2023-10-01-bug-report.md`
3. issues should include the following sections:
   - **Title**: A clear and concise title for the issue.
   - **Date**: The date of the issue creation or update.
   - **Description**: A detailed description of the issue, including steps to reproduce if applicable.
   - **Status**: The current status of the issue (e.g., open, in progress, resolved).
   - **Comments**: Any additional comments or discussions related to the issue.   


# Writing Tests Guidelines
1. initialieze the tests/ directory with `uv pytest --init` to create the necessary structure and add a README file.
2. update the README file in the `tests/` directory to include the following sections:
   - **Purpose**: A brief description of the purpose of the tests.
   - **Running Tests**: Instructions on how to run the tests, including any necessary setup steps.
   - **Contributing**: Guidelines for contributing new tests or modifying existing ones.
3. place tests in the `tests/` directory, all tests should be in Python format
4. tests should be named in the format `test_<module_name>.py`, e.g., `test_example.py`
5. tests should include the following sections:
   - **Imports**: Import necessary modules and functions.
   - **Test Functions**: Define test functions using the `def` keyword, with names starting with `test_`.
   - **Assertions**: Use assertions to check expected outcomes, e.g., `assert result == expected`.
   - **Setup and Teardown**: If needed, use setup and teardown methods to prepare and clean up before and after tests.
6. tests should be organized in a way that reflects the structure of the codebase, with related tests grouped together.
7. do not add tests to the `tests/` directory that are not related to the codebase, such as tests for external libraries or frameworks.
8. do not add tests that are already present in the test suite or included in the README file.
9. do not add tests that are not relevant to the codebase, such as tests for deprecated features or functionality.