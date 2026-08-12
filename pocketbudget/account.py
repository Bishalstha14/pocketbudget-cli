"""Domain: budgeting rules and protected account state."""

from pocketbudget.exceptions import InvalidTransactionError, OverdraftError

Transaction = tuple[str, int]


class Account:
    """An account whose balance only changes via validated transactions."""

    def __init__(self) -> None:
        self._balance = 0
        self._history: list[Transaction] = []

    @property
    def balance(self) -> int:
        """The current balance, readable from outside."""
        return self._balance

    @property
    def history(self) -> list[Transaction]:
        """A copy of the history; mutating it changes nothing on the account."""
        return self._history.copy()

    def add_income(self, amount: int) -> None:
        """Validate and add income to the balance."""
        if amount < 0:
            raise InvalidTransactionError("Income must be positive.")
        self._balance += amount
        self._history.append(("income", amount))

    def add_expense(self, amount: int) -> None:
        """Validate and deduct an expense from the balance."""
        if amount < 0:
            raise InvalidTransactionError("Expense must be positive.")
        if amount > self._balance:
            raise OverdraftError("these cannot be possible.")
        self._balance -= amount
        self._history.append(("expense", amount))
