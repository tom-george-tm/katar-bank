# **UV Command Reference Guide for Development Setup**

This document provides a concise and structured reference for using [**uv**](https://github.com/astral-sh/uv), a fast Python package manager, during the development lifecycle. It outlines essential commands for environment setup, dependency management, and synchronization for both production and development needs.

---

## **1. Installing UV**

To begin using `uv`, install it via `pip`:

```bash
pip install uv
```

---

## **2. Project Initialization**

When setting up a new project with `uv` for the first time, run:

```bash
uv init
```

---

## **3. Creating a Virtual Environment and Lock File**

You can create a virtual environment and generate a lock file separately:

* Create the `.venv` directory:

  ```bash
  uv venv
  ```

* Generate the `uv.lock` file:

  ```bash
  uv lock
  ```

Alternatively, you can perform both actions in a single command:

```bash
uv sync
```

---

## **4. Managing Dependencies**

### 4.1 Adding Packages

* **Production Dependencies**:

  ```bash
  uv add <package>
  ```

* **Development Dependencies**:

  ```bash
  uv add --group develop <package>
  ```

### 4.2 Removing Packages

* **Production Dependencies**:

  ```bash
  uv remove <package>
  ```

* **Development Dependencies**:

  ```bash
  uv remove --group develop <package>
  ```

---

## **5. Synchronizing Dependencies**

* **Install only production dependencies**:

  ```bash
  uv sync
  ```

* **Install both production and development dependencies**:

  ```bash
  uv sync --group develop
  ```

---

## **Notes**

* Always ensure that the `uv.lock` file is committed to version control to maintain reproducibility across environments.
* Use `uv sync` regularly to keep the local environment consistent with the lock file.
