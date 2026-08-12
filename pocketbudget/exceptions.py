"""Custom domain exceptions."""


class InvalidTransactionError(Exception):
    """Raised when a transaction is not valid."""


class OverdraftError(Exception):
    """Raised when an expense would overdraw the balance."""


class CorruptedDataError(Exception):
    """Raised when saved data is unreadable or inconsistent."""


class BudgetLimitError(Exception):
    """Raised when an expense would exceed a category's budget."""
