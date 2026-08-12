"""CLI tests: command routing, output, and persistence across invocations."""

from pathlib import Path

import pytest

from pocketbudget import cli


def _path(tmp_path: Path) -> Path:
    return tmp_path / "budget.json"


def test_no_arguments_prints_help(capsys: pytest.CaptureFixture[str]) -> None:
    cli.main([])

    assert "usage" in capsys.readouterr().out


def test_add_income_records_and_prints_confirmation(
    capsys: pytest.CaptureFixture[str],
    tmp_path: Path,
) -> None:
    path = _path(tmp_path)

    cli.main(["add-income", "100", "general"], path=path)
    assert "Recorded income of $100" in capsys.readouterr().out

    cli.main(["show-balance"], path=path)
    assert "Balance: $100" in capsys.readouterr().out


def test_add_expense_decreases_balance(
    capsys: pytest.CaptureFixture[str],
    tmp_path: Path,
) -> None:
    path = _path(tmp_path)
    cli.main(["add-income", "200", "general"], path=path)

    cli.main(["add-expense", "40", "entertainment"], path=path)

    cli.main(["show-balance"], path=path)
    assert "Balance: $160" in capsys.readouterr().out


def test_expense_over_budget_is_blocked_with_error(
    capsys: pytest.CaptureFixture[str],
    tmp_path: Path,
) -> None:
    path = _path(tmp_path)
    cli.main(["add-income", "300", "general"], path=path)
    cli.main(["set-budget", "entertainment", "100"], path=path)
    capsys.readouterr()

    cli.main(["add-expense", "150", "entertainment"], path=path)
    assert "budget" in capsys.readouterr().err

    cli.main(["show-balance"], path=path)
    assert "Balance: $300" in capsys.readouterr().out


def test_expense_overdraft_is_blocked_with_error(
    capsys: pytest.CaptureFixture[str],
    tmp_path: Path,
) -> None:
    path = _path(tmp_path)

    cli.main(["add-expense", "50", "general"], path=path)

    assert "Error" in capsys.readouterr().err


def test_show_history_lists_transactions(
    capsys: pytest.CaptureFixture[str],
    tmp_path: Path,
) -> None:
    path = _path(tmp_path)
    cli.main(["add-income", "100", "general"], path=path)
    cli.main(["add-expense", "40", "entertainment"], path=path)

    cli.main(["show-history"], path=path)

    out = capsys.readouterr().out
    assert "income: $100" in out
    assert "expense: $40" in out


def test_show_history_is_empty_for_fresh_account(
    capsys: pytest.CaptureFixture[str],
    tmp_path: Path,
) -> None:
    cli.main(["show-history"], path=_path(tmp_path))

    assert "No transactions yet" in capsys.readouterr().out


def test_set_budget_prints_confirmation(
    capsys: pytest.CaptureFixture[str],
    tmp_path: Path,
) -> None:
    cli.main(["set-budget", "entertainment", "100"], path=_path(tmp_path))

    assert "Set entertainment budget to $100" in capsys.readouterr().out


def test_show_summary_shows_spending_against_budgets(
    capsys: pytest.CaptureFixture[str],
    tmp_path: Path,
) -> None:
    path = _path(tmp_path)
    cli.main(["add-income", "500", "general"], path=path)
    cli.main(["set-budget", "entertainment", "100"], path=path)
    cli.main(["add-expense", "40", "entertainment"], path=path)
    cli.main(["add-expense", "200", "utilities"], path=path)

    cli.main(["show-summary"], path=path)

    out = capsys.readouterr().out
    assert "entertainment: $40 / $100" in out
    assert "utilities: $200 / no budget" in out


def test_budgets_persist_across_invocations(
    capsys: pytest.CaptureFixture[str],
    tmp_path: Path,
) -> None:
    path = _path(tmp_path)
    cli.main(["set-budget", "entertainment", "100"], path=path)
    cli.main(["add-income", "200", "general"], path=path)
    cli.main(["add-expense", "80", "entertainment"], path=path)

    cli.main(["show-summary"], path=path)

    assert "entertainment: $80 / $100" in capsys.readouterr().out


def test_corrupted_data_file_reports_error_without_crashing(
    capsys: pytest.CaptureFixture[str],
    tmp_path: Path,
) -> None:
    path = _path(tmp_path)
    path.write_text("{broken json", encoding="utf-8")

    cli.main(["show-balance"], path=path)

    assert "Error" in capsys.readouterr().err
