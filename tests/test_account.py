import pytest

from pocketbudget.account import Account
from pocketbudget.exceptions import InvalidTransactionError, OverdraftError


def test_balance_starts_at_zero() -> None:
    account = Account()
    assert account.balance == 0


def test_balance_can_be_read_from_outside() -> None:
    account = Account()
    account.add_income(100)
    assert account.balance == 100


def test_balance_cannot_be_assigned_from_outside() -> None:
    account = Account()
    with pytest.raises(AttributeError):
        account.balance = 500  # type: ignore[misc]


def test_add_income_increases_balance() -> None:
    account = Account()
    account.add_income(100)
    assert account.balance == 100


def test_add_expense_decreases_balance() -> None:
    account = Account()
    account.add_income(100)
    account.add_expense(40)
    assert account.balance == 60


def test_negative_income_is_rejected() -> None:
    account = Account()
    with pytest.raises(InvalidTransactionError):
        account.add_income(-50)
    assert account.balance == 0


def test_negative_expense_is_rejected() -> None:
    account = Account()
    account.add_income(100)
    with pytest.raises(InvalidTransactionError):
        account.add_expense(-50)
    assert account.balance == 100


def test_overdraw_is_blocked_and_replied() -> None:
    account = Account()
    account.add_income(100)
    with pytest.raises(OverdraftError, match="these cannot be possible"):
        account.add_expense(150)
    assert account.balance == 100
