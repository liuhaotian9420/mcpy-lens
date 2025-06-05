---
applyTo: '**'
---

Implementation of ANY feature or change in the project must follow a structured plan, execution, and review process.

# Plan, Execute, and Review Guidelines
## Plan Stage
- Plan files are always placed in the `plans/` directory, all plans should be in Markdown format.
- Plan files should be named in the format `YYYY-MM-DD-<plan-name>.md`, e.g., `2023-10-01-new-feature.md`.
- Plan files should include the following sections:
  - **Title**: A clear and concise title for the plan.
  - **Date**: The date of the plan creation or update.
  - **Description**: A brief description of the plan's purpose and goals.
  - **Tasks**: A list of tasks to be completed, with checkboxes for tracking progress.
  - **Notes**: Any additional notes or comments related to the plan.
- When creating a plan, ensure it is detailed enough to guide the execution phase, including specific tasks, expected outcomes, and any dependencies.

## Execute
- Review the plan and mark the dependencies between tasks.
- Revise the plan according to the dependencies and any additional insights gained during the review.
- Execute the plan by following the tasks outlined in the plan file.
- Actively ensure to document progress and any issues encountered during execution.
- **DO NOT WRITE TESTS TO DEBUG, LOOK AT THE CODE TO FIGURE OUT WHAT IS WRONG**.
- **DO NOT MAKE ATTEMPTS TO FIX ISSUES BY WRITING DIFFERENT COMMANDS. VIEW CODE AND DOCUMENTATION TO UNDERSTAND THE EXPECTED BEHAVIOR**
- If you encounter issues that require changes to the plan, update the plan file accordingly and document the changes.
- **You are NOT allowed to recreate files or directories that already exist unless explicitly stated in the plan. If a file or directory is missing, it should be created as part of the plan execution.**


# Review
- After executing the plan, conduct a review to assess the following:
  - **Completion**: Ensure all tasks in the plan have been completed.
  - **Quality**: Verify that the implementation meets the quality standards set in the plan.
  - **Documentation**: Check that all relevant documentation has been updated to reflect the changes made.
  - **Testing**: Ensure that tests have been written and executed to validate the changes. **Do NOT DIVE TOO DEEP into testing, just ensure that tests exist and pass.**
  - **Reusability**: Confirm that the code is modular and reusable, adhering to the project's coding standards.
- Append the review results to the plan file under a new section called **Review**
