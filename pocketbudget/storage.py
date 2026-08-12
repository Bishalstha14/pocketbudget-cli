"""Storage: saving and loading application state."""

import json
import os
from pathlib import Path

from pocketbudget.account import Account, Transaction
from pocketbudget.exceptions import CorruptedDataError

DEFAULT_PATH = Path("data") / "budget.json"

_TRANSACTION_KINDS = ("income", "expense")


def save(account: Account, path: Path | str = DEFAULT_PATH) -> None:
    """Write the account's state to a JSON file, atomically."""
    target = Path(path)
    target.parent.mkdir(parents=True, exist_ok=True)
    payload = {
        "balance": account.balance,
        "history": [list(entry) for entry in account.history],
        "budgets": account.budgets,
    }
    _atomic_write(target, json.dumps(payload))


def _atomic_write(target: Path, content: str) -> None:
    """Write ``content`` so a failure never leaves ``target`` partially written."""
    temp = target.with_name(f"{target.name}.tmp")
    try:
        temp.write_text(content, encoding="utf-8")
        os.replace(temp, target)
    except BaseException:
        temp.unlink(missing_ok=True)
        raise


def load(path: Path | str = DEFAULT_PATH) -> Account:
    """Rebuild an account from a saved file, validating everything it reads."""
    source = Path(path)
    if not source.exists():
        return Account()
    balance, history, budgets = _read_payload(source)
    return _build_account(balance, history, budgets)


def _read_payload(source: Path) -> tuple[int, list[object], dict[str, object]]:
    try:
        raw = json.loads(source.read_text(encoding="utf-8"))
    except json.JSONDecodeError as exc:
        raise CorruptedDataError(f"Invalid JSON in {source}: {exc}") from exc
    if not isinstance(raw, dict):
        raise CorruptedDataError("Saved data must be a JSON object.")
    try:
        balance = raw["balance"]
        history = raw["history"]
    except KeyError as exc:
        raise CorruptedDataError(f"Malformed saved data: missing {exc}.") from exc
    if isinstance(balance, bool) or not isinstance(balance, int):
        raise CorruptedDataError("Saved balance must be an integer.")
    if not isinstance(history, list):
        raise CorruptedDataError("Saved history must be a list.")
    budgets = raw.get("budgets", {})
    if not isinstance(budgets, dict):
        raise CorruptedDataError("Saved budgets must be an object.")
    return balance, history, budgets


def _build_account(
    balance: int,
    history: list[object],
    budgets: dict[str, object],
) -> Account:
    account = Account()
    _apply_budgets(account, budgets)
    for entry in history:
        kind, category, amount = _coerce_entry(entry)
        if kind == "income":
            account.add_income(amount)
        elif kind == "expense":
            account.add_expense(amount, category)
    if account.balance != balance:
        raise CorruptedDataError(
            f"Saved balance {balance} does not match history-derived "
            f"balance {account.balance}."
        )
    return account


def _apply_budgets(account: Account, budgets: dict[str, object]) -> None:
    for category, limit in budgets.items():
        if isinstance(limit, bool) or not isinstance(limit, int):
            raise CorruptedDataError(f"Malformed budget limit for {category!r}.")
        account.set_budget(category, limit)


def _coerce_entry(entry: object) -> Transaction:
    if not isinstance(entry, list) or len(entry) != 3:
        raise CorruptedDataError(f"Malformed transaction entry: {entry!r}.")
    kind, category, amount = entry
    if (
        kind not in _TRANSACTION_KINDS
        or not isinstance(category, str)
        or isinstance(amount, bool)
        or not isinstance(amount, int)
    ):
        raise CorruptedDataError(f"Malformed transaction entry: {entry!r}.")
    return kind, category, amount
