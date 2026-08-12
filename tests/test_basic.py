import subprocess
import sys


def test_cli_entry_point_exists_and_runs() -> None:
    result = subprocess.run(
        [sys.executable, "-m", "pocketbudget.cli"],
        capture_output=True,
        text=True,
    )
    assert result.returncode == 0
