# Contributing to ERPNext Meet

Thank you for your interest in contributing to ERPNext Meet! This document explains how to set up your development environment and submit changes.

## Development Setup

### Prerequisites

- Python 3.10+
- Node.js 18+
- A working [Frappe Bench](https://frappeframework.com/docs/user/en/installation) installation
- ERPNext installed on your bench

### Install the App

```bash
cd $PATH_TO_YOUR_BENCH
bench get-app https://github.com/alpkanoz/erpnext_meet --branch main
bench install-app erpnext_meet
```

### Set Up Pre-commit Hooks

This project uses `pre-commit` for code formatting and linting:

```bash
cd apps/erpnext_meet
pip install pre-commit
pre-commit install
```

The following tools are configured:

| Tool | Purpose |
|---|---|
| **ruff** | Python linting and formatting |
| **eslint** | JavaScript linting |
| **prettier** | JavaScript/JSON formatting |
| **pyupgrade** | Python syntax modernization |

## How to Contribute

### 1. Fork the Repository

Fork [alpkanoz/erpnext_meet](https://github.com/alpkanoz/erpnext_meet) on GitHub.

### 2. Create a Feature Branch

```bash
git checkout main
git pull origin main
git checkout -b feature/your-feature-name
```

**Branch naming conventions:**
- `feature/description` — New features
- `fix/description` — Bug fixes
- `docs/description` — Documentation updates

### 3. Make Your Changes

- Follow the existing code style (enforced by pre-commit)
- Write clear, descriptive commit messages

**Commit message format:**
```
type: short description

Optional longer description explaining the change.
```

Types: `feat`, `fix`, `docs`, `chore`, `refactor`, `test`

### 4. Test Your Changes

```bash
# Run the development server
bench start

# Build assets
bench build --app erpnext_meet
```

### 5. Submit a Pull Request

- Push your branch to your fork
- Open a Pull Request against the `main` branch
- Provide a clear description of your changes
- Reference any related issues

## Project Structure

```
erpnext_meet/
├── erpnext_meet/
│   ├── erpnext_meet/
│   │   ├── api.py              # API endpoints (JWT, webhooks, room management)
│   │   ├── doctype/
│   │   │   ├── meeting/        # Main Meeting DocType
│   │   │   ├── meeting_participant/  # Participant child table
│   │   │   └── meeting_settings/     # App settings (singleton)
│   │   └── workspace/          # ERPNext workspace definition
│   ├── hooks.py                # App hooks and configuration
│   ├── tasks.py                # Scheduled tasks (meeting lifecycle)
│   ├── public/js/              # Client-side JavaScript
│   ├── templates/              # Email templates
│   └── translations/           # Translation files
├── jitsi_setup/                # Jitsi configuration files
│   ├── env.example
│   ├── jitsi-meet.cfg.lua.example
│   └── prosody-plugins-custom/ # Custom Prosody plugins
├── docs/                       # Documentation
└── pyproject.toml
```

## Code of Conduct

Be respectful, inclusive, and constructive. We are building this together.

## Questions?

Open an issue on GitHub or reach out via the ERPNext community forums.
