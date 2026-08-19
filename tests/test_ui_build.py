import subprocess
from pathlib import Path

def test_ui_build() -> None:
    """
    Automated test that verifies the React/Vite UI builds cleanly without compilation/JSX errors.
    """
    ui_dir = Path(__file__).parent.parent / "ui"
    result = subprocess.run(
        "npm run build",
        cwd=str(ui_dir),
        shell=True,
        capture_output=True,
        text=True
    )
    assert result.returncode == 0, f"UI build failed with errors:\n{result.stdout}\n{result.stderr}"
