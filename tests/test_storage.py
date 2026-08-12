"""Storage tests: save/load round-trip, missing file, and corruption handling."""

import json
from pathlib import Path

import pytest

from pocketbudget.account import Account
from pocketbudget.exceptions import (
    CorruptedDataError,
    InvalidTransactionError,
    OverdraftError,
)
from pocketbudget.storage import DEFAULT_PATH, load, save


def _write(path: Path, content: object) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(content), encoding="utf-8")


def test_default_path_is_in_dedicated_data_folder() -> None:
    assert DEFAULT_PATH == Path("data") / "budget.json"


def test_save_creates_parent_directory_and_file(tmp_path: Path) -> None:
    path = tmp_path / "nested" / "budget.json"
    account = Account()
    account.add_income(100)

    save(account, path)

    assert path.is_file()


def test_saved_file_contains_balance_and_history(tmp_path: Path) -> None:
    path = tmp_path / "budget.json"
    account = Account()
    account.add_income(100)

    save(account, path)

    data = json.loads(path.read_text(encoding="utf-8"))
    assert data == {"balance": 100, "history": [["income", "", 100]], "budgets": {}}


def test_round_trip_preserves_balance_and_history(tmp_path: Path) -> None:
    path = tmp_path / "budget.json"
    account = Account()
    account.add_income(100)
    account.add_expense(40)

    save(account, path)
    loaded = load(path)

    assert isinstance(loaded, Account)
    assert loaded.balance == 60
    assert loaded.history == [("income", "", 100), ("expense", "general", 40)]


def test_round_trip_preserves_empty_account(tmp_path: Path) -> None:
    path = tmp_path / "budget.json"

    save(Account(), path)
    loaded = load(path)

    assert loaded.balance == 0
    assert loaded.history == []


def test_round_trip_preserves_budgets(tmp_path: Path) -> None:
    path = tmp_path / "budget.json"
    account = Account()
    account.set_budget("entertainment", 100)
    account.set_budget("utilities", 300)

    save(account, path)
    loaded = load(path)

    assert loaded.budgets == {"entertainment": 100, "utilities": 300}


def test_load_missing_file_returns_clean_account(tmp_path: Path) -> None:
    loaded = load(tmp_path / "does-not-exist.json")

    assert isinstance(loaded, Account)
    assert loaded.balance == 0
    assert loaded.history == []


def test_load_missing_file_does_not_create_it(tmp_path: Path) -> None:
    path = tmp_path / "does-not-exist.json"

    load(path)

    assert not path.exists()


def test_load_invalid_json_raises_corrupted_data_error(tmp_path: Path) -> None:
    path = tmp_path / "budget.json"
    path.write_text("{not valid json", encoding="utf-8")

    with pytest.raises(CorruptedDataError):
        load(path)


def test_load_wrong_top_level_type_raises_corrupted_data_error(
    tmp_path: Path,
) -> None:
    path = tmp_path / "budget.json"
    _write(path, ["income", 100])

    with pytest.raises(CorruptedDataError):
        load(path)


def test_load_missing_keys_raises_corrupted_data_error(tmp_path: Path) -> None:
    path = tmp_path / "budget.json"
    _write(path, {"balance": 0})

    with pytest.raises(CorruptedDataError):
        load(path)


def test_load_non_integer_balance_raises_corrupted_data_error(
    tmp_path: Path,
) -> None:
    path = tmp_path / "budget.json"
    _write(path, {"balance": "zero", "history": []})

    with pytest.raises(CorruptedDataError):
        load(path)


def test_load_balance_mismatch_raises_corrupted_data_error(
    tmp_path: Path,
) -> None:
    path = tmp_path / "budget.json"
    _write(path, {"balance": 999, "history": [["income", "", 100]]})

    with pytest.raises(CorruptedDataError):
        load(path)


def test_load_malformed_transaction_entry_raises_corrupted_data_error(
    tmp_path: Path,
) -> None:
    path = tmp_path / "budget.json"
    _write(path, {"balance": 0, "history": [["income"]]})

    with pytest.raises(CorruptedDataError):
        load(path)


def test_load_unknown_transaction_kind_raises_corrupted_data_error(
    tmp_path: Path,
) -> None:
    path = tmp_path / "budget.json"
    _write(path, {"balance": 0, "history": [["gift", "", 100]]})

    with pytest.raises(CorruptedDataError):
        load(path)


def test_load_negative_amount_rejected_like_live_data(tmp_path: Path) -> None:
    path = tmp_path / "budget.json"
    _write(path, {"balance": -50, "history": [["income", "", -50]]})

    with pytest.raises(InvalidTransactionError):
        load(path)


def test_load_overdraft_rejected_like_live_data(tmp_path: Path) -> None:
    path = tmp_path / "budget.json"
    _write(
        path,
        {"balance": 50, "history": [["income", "", 100], ["expense", "general", 150]]},
    )

    with pytest.raises(OverdraftError):
        load(path)


def test_load_negative_budget_limit_rejected_like_live_data(
    tmp_path: Path,
) -> None:
    path = tmp_path / "budget.json"
    _write(
        path,
        {"balance": 0, "history": [], "budgets": {"entertainment": -50}},
    )

    with pytest.raises(InvalidTransactionError):
        load(path)
