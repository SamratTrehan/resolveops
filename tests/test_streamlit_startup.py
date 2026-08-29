import os
from pathlib import Path
import subprocess
import sys


ROOT = Path(__file__).resolve().parents[1]


def test_streamlit_app_imports_without_api_key() -> None:
    environment = os.environ.copy()
    environment.pop("OPENAI_API_KEY", None)

    result = subprocess.run(
        [sys.executable, "-c", "import streamlit_app"],
        cwd=ROOT,
        env=environment,
        capture_output=True,
        text=True,
        timeout=30,
        check=False,
    )

    assert result.returncode == 0, result.stderr
