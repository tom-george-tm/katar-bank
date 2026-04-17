# Project Git Workflow and Conventions

This document outlines the Git branching strategy, continuous deployment (CD) flow, and commit message conventions for the project, tailored for a small team of developers to minimize complexity.

---

## Git Flow

### Long-Living Branches

- **main**:
  The primary branch representing the production-ready codebase. It is stable and only updated with thoroughly tested and approved changes.

- **develop**:
  A long-living branch created from `main`. It serves as the integration branch for features and fixes, reflecting the latest development state.

### Feature and Fix Branches

#### Feature Branches

- Created from the `develop` branch for new features or enhancements.
- **Naming convention**:
  `feature/<issue-id>-<shortname>` (e.g., `feature/123-add-login-page`)
- Use lowercase letters and hyphens (`-`) instead of underscores (`_`).

#### Fix Branches

- Created from the `develop` branch for bug fixes, including urgent production issues.
- **Naming convention**:
  `fix/<issue-id>-<shortname>` (e.g., `fix/456-login-error`)
- Use lowercase letters and hyphens (`-`) instead of underscores (`_`).
- For urgent production fixes, prioritize PR review and merging to `develop`, followed by a fast-tracked merge to `main`.

---

## Branch Workflow

1. Create feature or fix branches from the `develop` branch.
2. Develop and commit changes to the respective feature or fix branch.
3. Create a pull request (PR) to merge the branch into `develop`.
4. PRs require at least one approval from a reviewer.
5. Merge the PR into `develop` using a **merge commit** to preserve the branch’s history (no squashing).
6. Delete the feature or fix branch after merging to keep the repository clean.
7. When `develop` contains all desired features and is stable, create a PR to merge `develop` into `main`.
8. Merge the PR into `main` using a **merge commit** to maintain a clear release history (no squashing).
9. After validation and approval, apply a **version tag** to the `main` branch (e.g., `v1.0.0`) to mark stable releases.
10. Optionally, merge `main` back into `develop` to include any minor changes made during the PR process.

---

## Continuous Deployment (CD) Flow

- **Development Server**
  - **Trigger**: On successful PR merge to the `develop` branch
  - **Action**: Automatically deploy the `develop` branch to the development server for testing

- **Staging Server**
  - **Trigger**: On successful PR merge to the `main` branch
  - **Action**: Automatically deploy the `main` branch to the staging server for further validation

- **Production Server**
  - **Trigger**: When a version tag (e.g., `v1.0.0`) is added to the `main` branch
  - **Action**: Automatically deploy the tagged commit to the production server

---

## Commit Message Style

To maintain clarity and consistency, follow these commit message guidelines:

### Format

```
<type>(<scope>): <issue-id> <short description>
```

- `<type>`: Indicates the type of change (e.g., `feat`, `fix`, `docs`, `test`, `chore`, `refactor`)
- `<scope>`: Specifies the module or area affected (e.g., `login`, `api`, `ui`)
- `<issue-id>`: References the issue or ticket number (e.g., `123`)
- `<short description>`: A concise summary of the change (50 characters or less, lowercase, no period)

### Examples

- `feat(login): 123 add user authentication`
- `fix(api): 456 resolve null pointer exception`
- `docs(readme): 789 update installation instructions`
- `test(ui): 101 add unit tests for button component`
- `chore(deps): 202 update npm packages`
- `refactor(login): 303 simplify auth logic`

### Commit Types

- `feat`: A new feature or enhancement (e.g., adding a new UI component)
- `fix`: A bug fix or correction, including urgent production issues
- `docs`: Changes to documentation, like README or comments
- `test`: Additions or updates to tests, without changing production code
- `chore`: Routine maintenance tasks, like updating dependencies
- `refactor`: Code restructuring without changing functionality

### Guidelines

- Use present tense (e.g., "add" instead of "added")
- Keep the message clear and descriptive
- Avoid generic messages like "update" or "fix stuff"
- If more details are needed, add a blank line after the summary and include a detailed description

---

## Enabling Pre-Commit Hooks

[Pre-commit](https://pre-commit.com/) hooks are used to enforce code quality and consistency by running automated checks before each commit. These checks help catch issues early, such as formatting errors, linting violations, or missing tests, ensuring a cleaner codebase.

See [supported hooks](https://pre-commit.com/hooks.html) for more details

### Setup Instructions

1. **Install pre-commit**:
   Ensure the `pre-commit` package is installed in your project. If not already included, install it using:

   ```
   pip install pre-commit
   ```

2. **Configure pre-commit**:
   Verify that a `.pre-commit-config.yaml` file exists in the project root. This file defines the hooks to run, such as linters, formatters, or custom scripts.

3. **Install pre-commit hooks**:
   Run the following command to set up the pre-commit hooks in your local Git repository:

   ```
   pre-commit install
   ```

   This command configures Git to run the defined hooks automatically before each commit.

4. **Run pre-commit manually**:
   To manually run all pre-commit checks on all files (useful for initial setup or CI pipelines), use:

   ```
   pre-commit run --all-files
   ```

5. **Bypass pre-commit hooks (if needed)**:
   In rare cases, you may need to skip pre-commit checks for a specific commit (e.g., for temporary or non-code changes). Use the `--no-verify` flag:

   ```
   git commit --no-verify
   ```

   **Note**: Use this sparingly, as bypassing hooks can introduce issues into the codebase.

### Troubleshooting

- **Hook failures**: If a pre-commit hook fails, it will prevent the commit. Check the error output, fix the issues (e.g., formatting errors), and try committing again.
- **Update hooks**: To update hooks to their latest versions, run:

  ```
  pre-commit autoupdate
  ```

- **Clear cache**: If hooks are slow or behaving unexpectedly, clear the pre-commit cache:

  ```
  pre-commit clean
  ```

### Best Practices

- Always run `pre-commit install` after cloning the repository to ensure hooks are active.
- Regularly update the `.pre-commit-config.yaml` file to include new or updated hooks as the project evolves.
- Ensure all team members have pre-commit installed to maintain consistency across commits.
- Integrate pre-commit checks into your CI pipeline to enforce the same standards on pull requests.
