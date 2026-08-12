from pocketbudget.account import Account


def test_mutating_returned_history_does_not_change_account() -> None:
    account = Account()
    account.add_income(100)
    account.add_expense(40)

    returned_history = account.history
    returned_history.clear()
    returned_history.append("tampered")  # type: ignore[arg-type]

    assert len(account.history) == 2
