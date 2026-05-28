---
name: ship-it
description: Standard development workflow — check git status, plan steps, implement features before tests, verify each step's input/output, then push after each confirmed step.
---

Follow this workflow for every task:

1. **Check git status**
   Run `git status` first. If there are uncommitted changes, explain them before proceeding.

2. **Plan the steps**
   List the full implementation plan. For each step, describe:
   - What will be done
   - Which files will be created or modified
   - Expected input and output

   Wait for user confirmation before starting.

3. **Implement step by step (features first, tests after)**
   - Implement features first, write tests after all features are complete.
   - After each step, verify the input and output match expectations (e.g. run build, test in browser, inspect output).
   - Do not move to the next step until the current one is confirmed.

4. **Update README.md**
   After all steps are implemented and confirmed, update `README.md` to reflect any changes:
   - New features or commands
   - Changed file structure
   - New environment variables or configuration

5. **Push after each confirmed step**
   Once a step is verified and confirmed by the user:
   - Stage the relevant files with `git add`
   - Write a clear commit message (no co-author)
   - Run `git push`
   - Then proceed to the next step.
