"""CLI: user input and command routing."""

import argparse
import sys
from collections.abc import Callable
from pathlib import Path

from pocketbudget.account import Account
from pocketbudget.exceptions import (
    BudgetLimitError,
    CorruptedDataError,
    InvalidTransactionError,
    OverdraftError,
)
from pocketbudget.storage import DEFAULT_PATH, load, save

_MUTATING_COMMANDS = {"add-income", "add-expense", "set-budget"}

_Handler = Callable[[argparse.Namespace, Account], None]


def _build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(prog="pocketbudget")
    subparsers = parser.add_subparsers(dest="command")

    add_income = subparsers.add_parser("add-income", help="record a safe deposit")
    add_income.add_argument("amount", type=int)
    add_income.add_argument("category")

    add_expense = subparsers.add_parser("add-expense", help="record an expense")
    add_expense.add_argument("amount", type=int)
    add_expense.add_argument("category")

    subparsers.add_parser("show-balance", help="print the current balance")

    subparsers.add_parser("show-history", help="list all transactions")

    set_budget = subparsers.add_parser("set-budget", help="set a category budget")
    set_budget.add_argument("category")
    set_budget.add_argument("limit", type=int)

    subparsers.add_parser("show-summary", help="show spending against budgets")

    return parser


def main(argv: list[str] | None = None, *, path: Path = DEFAULT_PATH) -> int:
    """Run the PocketBudget CLI against the account file at ``path``."""
    parser = _build_parser()
    args = parser.parse_args(argv)
    if args.command is None:
        parser.print_help()
        return 0
    try:
        account = load(path)
        _dispatch(args, account)
        if args.command in _MUTATING_COMMANDS:
            save(account, path)
    except (
        BudgetLimitError,
        CorruptedDataError,
        InvalidTransactionError,
        OverdraftError,
    ) as exc:
        print(f"Error: {exc}", file=sys.stderr)
        return 1
    except Exception as exc:
        print(f"Unexpected error: {exc}", file=sys.stderr)
        return 1
    return 0


def _dispatch(args: argparse.Namespace, account: Account) -> None:
    handlers: dict[str, _Handler] = {
        "add-income": _add_income,
        "add-expense": _add_expense,
        "show-balance": _show_balance,
        "show-history": _show_history,
        "set-budget": _set_budget,
        "show-summary": _show_summary,
    }
    handler = handlers.get(args.command)
    if handler is not None:
        handler(args, account)


def _add_income(args: argparse.Namespace, account: Account) -> None:
    account.add_income(args.amount)
    print(f"Recorded income of ${args.amount}.")


def _add_expense(args: argparse.Namespace, account: Account) -> None:
    account.add_expense(args.amount, args.category)
    print(f"Recorded expense of ${args.amount} in {args.category}.")


def _show_balance(args: argparse.Namespace, account: Account) -> None:
    print(f"Balance: ${account.balance}")


def _show_history(args: argparse.Namespace, account: Account) -> None:
    if not account.history:
        print("No transactions yet.")
        return
    for kind, _category, amount in account.history:
        print(f"{kind}: ${amount}")


def _set_budget(args: argparse.Namespace, account: Account) -> None:
    account.set_budget(args.category, args.limit)
    print(f"Set {args.category} budget to ${args.limit}.")


def _show_summary(args: argparse.Namespace, account: Account) -> None:
    categories = sorted(set(account.budgets) | set(account.spending))
    if not categories:
        print("No budgets or spending yet.")
        return
    for category in categories:
        spent = account.spending.get(category, 0)
        limit = account.budgets.get(category)
        if limit is None:
            print(f"{category}: ${spent} / no budget")
        else:
            print(f"{category}: ${spent} / ${limit}")


if __name__ == "__main__":
    raise SystemExit(main())
