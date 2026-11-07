"""Domain: budgeting rules and protected account state."""

from pocketbudget.exceptions import (
    BudgetLimitError,
    InvalidTransactionError,
    OverdraftError,
)

Transaction = tuple[str, str, int]


class Account:
    """An account whose balance only changes via validated transactions."""

    def __init__(self) -> None:
        self._balance = 0
        self._history: list[Transaction] = []
        self._budgets: dict[str, int] = {}
        self._spending: dict[str, int] = {}

    @property
    def balance(self) -> int:
        """The current balance, readable from outside."""
        return self._balance

    @property
    def history(self) -> list[Transaction]:
        """A copy of the history; mutating it changes nothing on the account."""
        return self._history.copy()

    @property
    def budgets(self) -> dict[str, int]:
        """A copy of the category budgets; mutating it changes nothing."""
        return self._budgets.copy()

    @property
    def spending(self) -> dict[str, int]:
        """A copy of per-category spending; mutating it changes nothing."""
        return self._spending.copy()

    def add_income(self, amount: int) -> None:
        """Validate, then add income to the balance."""
        self._validate_positive(amount, "Income")
        self._balance += amount
        self._history.append(("income", "", amount))

    def add_expense(self, amount: int, category: str = "general") -> None:
        """Validate, then deduct an expense from the balance."""
        self._validate_positive(amount, "Expense")
        self._validate_overdraft(amount)
        self._validate_budget(amount, category)
        self._balance -= amount
        self._history.append(("expense", category, amount))
        self._spending[category] = self._spending.get(category, 0) + amount

    def set_budget(self, category: str, limit: int) -> None:
        """Validate, then set the spending limit for a category."""
        self._validate_positive(limit, "Budget limit")
        self._budgets[category] = limit
        self._spending.setdefault(category, 0)

    def _validate_positive(self, amount: int, label: str) -> None:
        if amount <= 0:
            raise InvalidTransactionError(f"{label} must be positive.")

    def _validate_overdraft(self, amount: int) -> None:
        if amount > self._balance:
            raise OverdraftError("these cannot be possible.")

    def _validate_budget(self, amount: int, category: str) -> None:
        limit = self._budgets.get(category)
        if limit is not None and self._spending.get(category, 0) + amount > limit:
            raise BudgetLimitError(
                f"Expense would exceed the {category} budget of {limit}."
            )
