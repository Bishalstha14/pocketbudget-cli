# PocketBudget

A command-line budget manager in Python. Record income and expenses against category budgets, and get a per-category summary — all from the terminal. Your balance, transaction history, and budgets are persisted to a JSON file, so nothing is lost between runs.

## Installation & Setup

```bash
python -m venv .venv
source .venv/bin/activate
pip install -e .
```

This installs the `pocketbudget` command. To enable the pre-commit checks (ruff, mypy, pytest) before every commit:

```bash
pre-commit install
```

## Usage

Run `pocketbudget <command>` (or `python -m pocketbudget`). State is stored in `data/budget.json`.

```bash
# Record a safe deposit
pocketbudget add-income 500 general

# Set a spending ceiling for a category
pocketbudget set-budget entertainment 100

# Record an expense (validated against the balance and the category budget)
pocketbudget add-expense 40 entertainment

# Print the current balance
pocketbudget show-balance

# List every executed transaction
pocketbudget show-history

# Show per-category spending against budgets
pocketbudget show-summary
```

When a rule is broken — a negative amount, an overdraft, an expense past a budget limit, or an unreadable save file — the CLI prints a short error to stderr and exits non-zero instead of showing a raw traceback.

## Running the Tests

```bash
python -m pytest
```

The suite covers the domain rules, JSON persistence, CLI routing, and error handling. Pre-commit runs `ruff`, `mypy --strict`, and `pytest` on every commit.

## Design Decisions

- **The balance is read-only from outside.** `Account.balance` is a property backed by `_balance`; there is no setter, so external code can't assign a balance directly.
- **Returned collections are copies.** `history`, `budgets`, and `spending` return copies, so mutating a returned value changes nothing on the account.
- **Rules live in the domain, never the CLI.** `Account` validates every transaction and budget before mutating any state, raising a distinct custom exception per rule (`InvalidTransactionError`, `OverdraftError`, `BudgetLimitError`, `CorruptedDataError`) so a caller can tell a blown budget apart from a corrupt save file.
- **Validate before you mutate.** All checks run first; state only changes once validation passes, so a failed operation leaves the account exactly as it was.
- **Loaded data passes through the same validation as live data.** Saving stores balance, history, and budgets; loading replays them through the same `Account` methods.
- **Saves are atomic.** Storage writes to a temp file and renames it into place, so a failed save never leaves a half-written data file.
