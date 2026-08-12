"""Error tests: domain classes reject bad data with the right exception."""

import json
import os
import subprocess
import sys
from pathlib import Path

import pytest

from pocketbudget.account import Account
from pocketbudget.exceptions import (
    BudgetLimitError,
    CorruptedDataError,
    InvalidTransactionError,
    OverdraftError,
)
from pocketbudget.storage import load

REPO_ROOT = Path(__file__).resolve().parents[1]


def _write(path: Path, content: object) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(content), encoding="utf-8")


def test_negative_income_raises_invalid_transaction_error() -> None:
    account = Account()

    with pytest.raises(InvalidTransactionError, match="Income must be positive"):
        account.add_income(-50)

    assert account.balance == 0


def test_negative_expense_raises_invalid_transaction_error() -> None:
    account = Account()
    account.add_income(100)

    with pytest.raises(InvalidTransactionError, match="Expense must be positive"):
        account.add_expense(-50, "entertainment")

    assert account.balance == 100


def test_negative_budget_limit_raises_invalid_transaction_error() -> None:
    account = Account()

    with pytest.raises(InvalidTransactionError, match="Budget limit must be positive"):
        account.set_budget("entertainment", -10)


def test_expense_past_strict_budget_limit_raises_budget_limit_error() -> None:
    account = Account()
    account.add_income(300)
    account.set_budget("entertainment", 100)

    with pytest.raises(BudgetLimitError, match="entertainment"):
        account.add_expense(150, "entertainment")

    assert account.balance == 300
    assert account.history == [("income", "", 300)]


def test_expense_overdraft_raises_overdraft_error() -> None:
    account = Account()
    account.add_income(100)

    with pytest.raises(OverdraftError, match="these cannot be possible"):
        account.add_expense(150, "entertainment")

    assert account.balance == 100


def test_corrupted_json_raises_corrupted_data_error(tmp_path: Path) -> None:
    path = tmp_path / "budget.json"
    path.write_text("{not valid json", encoding="utf-8")

    with pytest.raises(CorruptedDataError):
        load(path)


def test_non_object_top_level_raises_corrupted_data_error(tmp_path: Path) -> None:
    path = tmp_path / "budget.json"
    _write(path, ["income", "", 100])

    with pytest.raises(CorruptedDataError):
        load(path)


def test_missing_required_keys_raises_corrupted_data_error(tmp_path: Path) -> None:
    path = tmp_path / "budget.json"
    _write(path, {"balance": 0})

    with pytest.raises(CorruptedDataError):
        load(path)


def test_non_integer_balance_raises_corrupted_data_error(tmp_path: Path) -> None:
    path = tmp_path / "budget.json"
    _write(path, {"balance": "one hundred", "history": []})

    with pytest.raises(CorruptedDataError):
        load(path)


def test_balance_history_mismatch_raises_corrupted_data_error(
    tmp_path: Path,
) -> None:
    path = tmp_path / "budget.json"
    _write(path, {"balance": 999, "history": [["income", "", 100]]})

    with pytest.raises(CorruptedDataError):
        load(path)


def test_malformed_transaction_entry_raises_corrupted_data_error(
    tmp_path: Path,
) -> None:
    path = tmp_path / "budget.json"
    _write(path, {"balance": 0, "history": [["income"]]})

    with pytest.raises(CorruptedDataError):
        load(path)


def test_unknown_transaction_kind_raises_corrupted_data_error(
    tmp_path: Path,
) -> None:
    path = tmp_path / "budget.json"
    _write(path, {"balance": 0, "history": [["gift", "", 100]]})

    with pytest.raises(CorruptedDataError):
        load(path)


def test_overspend_and_unreadable_file_are_distinct_exceptions(
    tmp_path: Path,
) -> None:
    account = Account()
    account.add_income(300)
    account.set_budget("food", 100)
    with pytest.raises(BudgetLimitError):
        account.add_expense(150, "food")

    path = tmp_path / "budget.json"
    path.write_text("{not valid json", encoding="utf-8")
    with pytest.raises(CorruptedDataError):
        load(path)


def test_failed_income_leaves_state_unchanged() -> None:
    account = Account()
    account.add_income(100)
    account.set_budget("food", 200)

    with pytest.raises(InvalidTransactionError):
        account.add_income(-50)

    assert account.balance == 100
    assert account.history == [("income", "", 100)]
    assert account.spending == {"food": 0}
    assert account.budgets == {"food": 200}


def test_failed_expense_leaves_state_unchanged() -> None:
    account = Account()
    account.add_income(300)
    account.set_budget("food", 100)
    account.add_expense(40, "food")
    balance_before = account.balance
    history_before = account.history
    spending_before = account.spending
    budgets_before = account.budgets

    with pytest.raises(BudgetLimitError):
        account.add_expense(80, "food")

    assert account.balance == balance_before
    assert account.history == history_before
    assert account.spending == spending_before
    assert account.budgets == budgets_before


def _run_cli(*args: str, cwd: Path) -> subprocess.CompletedProcess[str]:
    env = dict(os.environ)
    env["PYTHONPATH"] = str(REPO_ROOT)
    return subprocess.run(
        [sys.executable, "-m", "pocketbudget.cli", *args],
        capture_output=True,
        text=True,
        cwd=cwd,
        env=env,
    )


def test_cli_negative_income_is_clean_error_without_traceback(
    tmp_path: Path,
) -> None:
    result = _run_cli("add-income", "-50", "general", cwd=tmp_path)

    assert "Error: Income must be positive" in result.stderr
    assert "Traceback" not in result.stderr
    assert result.returncode != 0


def test_cli_expense_overdraft_is_clean_error_without_traceback(
    tmp_path: Path,
) -> None:
    result = _run_cli("add-expense", "50", "food", cwd=tmp_path)

    assert "Error: these cannot be possible" in result.stderr
    assert "Traceback" not in result.stderr
    assert result.returncode != 0


def test_cli_expense_over_budget_is_clean_error_without_traceback(
    tmp_path: Path,
) -> None:
    _run_cli("add-income", "300", "general", cwd=tmp_path)
    _run_cli("set-budget", "food", "100", cwd=tmp_path)

    result = _run_cli("add-expense", "150", "food", cwd=tmp_path)

    assert "budget" in result.stderr
    assert "Traceback" not in result.stderr
    assert result.returncode != 0


def test_cli_negative_budget_is_clean_error_without_traceback(
    tmp_path: Path,
) -> None:
    result = _run_cli("set-budget", "food", "-10", cwd=tmp_path)

    assert "Budget limit must be positive" in result.stderr
    assert "Traceback" not in result.stderr
    assert result.returncode != 0


def test_cli_corrupted_file_is_clean_error_without_traceback(
    tmp_path: Path,
) -> None:
    data_dir = tmp_path / "data"
    data_dir.mkdir()
    (data_dir / "budget.json").write_text("{broken json", encoding="utf-8")

    result = _run_cli("show-balance", cwd=tmp_path)

    assert "Error" in result.stderr
    assert "Traceback" not in result.stderr
    assert result.returncode != 0


def test_failed_cli_expense_does_not_persist_partial_state(
    tmp_path: Path,
) -> None:
    _run_cli("add-income", "300", "general", cwd=tmp_path)
    _run_cli("set-budget", "food", "100", cwd=tmp_path)
    _run_cli("add-expense", "150", "food", cwd=tmp_path)

    result = _run_cli("show-balance", cwd=tmp_path)

    assert result.returncode == 0
    assert "Balance: $300" in result.stdout
