"""Budget tests: per-category spending limits enforced by the domain."""

import pytest

from pocketbudget.account import Account
from pocketbudget.exceptions import BudgetLimitError, InvalidTransactionError


def test_set_budget_does_not_change_balance() -> None:
    account = Account()

    account.set_budget("entertainment", 100)

    assert account.balance == 0


def test_expense_within_budget_is_allowed() -> None:
    account = Account()
    account.add_income(200)
    account.set_budget("entertainment", 100)

    account.add_expense(80, "entertainment")

    assert account.balance == 120


def test_expense_equal_to_limit_is_allowed() -> None:
    account = Account()
    account.add_income(200)
    account.set_budget("entertainment", 100)

    account.add_expense(100, "entertainment")

    assert account.balance == 100


def test_expense_over_budget_is_blocked() -> None:
    account = Account()
    account.add_income(200)
    account.set_budget("entertainment", 100)

    with pytest.raises(BudgetLimitError, match="entertainment"):
        account.add_expense(120, "entertainment")

    assert account.balance == 200


def test_budgets_are_checked_per_category() -> None:
    account = Account()
    account.add_income(500)
    account.set_budget("entertainment", 100)
    account.set_budget("utilities", 300)
    account.add_expense(90, "entertainment")
    account.add_expense(250, "utilities")

    with pytest.raises(BudgetLimitError, match="entertainment"):
        account.add_expense(20, "entertainment")

    account.add_expense(50, "utilities")

    assert account.balance == 110


def test_spending_accumulates_against_limit() -> None:
    account = Account()
    account.add_income(300)
    account.set_budget("entertainment", 100)
    account.add_expense(40, "entertainment")
    account.add_expense(40, "entertainment")

    with pytest.raises(BudgetLimitError, match="entertainment"):
        account.add_expense(30, "entertainment")

    assert account.balance == 220


def test_unbudgeted_category_is_unlimited() -> None:
    account = Account()
    account.add_income(1000)
    account.set_budget("entertainment", 100)

    account.add_expense(900, "utilities")

    assert account.balance == 100


def test_negative_budget_limit_is_rejected() -> None:
    account = Account()

    with pytest.raises(InvalidTransactionError):
        account.set_budget("entertainment", -10)


def test_blocked_expense_is_not_recorded_in_history() -> None:
    account = Account()
    account.add_income(200)
    account.set_budget("entertainment", 100)

    with pytest.raises(BudgetLimitError, match="entertainment"):
        account.add_expense(150, "entertainment")

    assert account.history == [("income", "", 200)]
