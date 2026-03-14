# Contributing to Email Campaign Manager

Thank you for your interest in contributing! All contributions — bug reports, feature requests, documentation improvements, and code changes — are welcome.

---

## Table of Contents

- [Reporting Issues](#reporting-issues)
- [Development Setup](#development-setup)
- [Coding Guidelines](#coding-guidelines)
- [Commit Message Style](#commit-message-style)
- [Pull Request Process](#pull-request-process)

---

## Reporting Issues

1. Search existing issues before opening a new one.
2. Include:
   - Python version (`python --version`)
   - OS and MongoDB version
   - Steps to reproduce the problem
   - Expected vs. actual behaviour
   - Any relevant log output or stack traces

---

## Development Setup

```bash
# 1. Fork and clone
git clone https://github.com/<your-fork>/Email_Camp.git
cd Email_Camp

# 2. Create a virtual environment
python -m venv .venv
source .venv/bin/activate  # Windows: .venv\Scripts\activate

# 3. Install dependencies
pip install -r requirements.txt

# 4. Configure environment
cp .env.example .env
# Edit .env with your local credentials

# 5. Verify setup
python test_setup.py
```

---

## Coding Guidelines

- Follow [PEP 8](https://peps.python.org/pep-0008/) for formatting and naming.
- Add or update **docstrings** for any public function or class you modify.
- Do not hardcode credentials — always use environment variables.
- Keep new dependencies minimal; add them to `requirements.txt` with a pinned minimum version.

---

## Commit Message Style

Use concise, imperative-mood messages:

```
feat: add CSV export for individual contact lists
fix: handle None custom_fields in personalize_email
docs: expand API_DOCUMENTATION with log methods
refactor: extract SMTP connection into helper method
```

Prefix tags: `feat`, `fix`, `docs`, `refactor`, `test`, `chore`.

---

## Pull Request Process

1. Create a branch from `main`:
   ```bash
   git checkout -b feature/my-feature
   ```
2. Make your changes and commit them.
3. Run the setup tests to confirm nothing is broken:
   ```bash
   python test_setup.py
   python smtp_test.py   # only if SMTP credentials are available
   ```
4. Push your branch and open a Pull Request against `main`.
5. Fill in the PR description — explain **what** changed and **why**.
6. Address any review comments.

All PRs must pass the existing verification scripts before being merged.
