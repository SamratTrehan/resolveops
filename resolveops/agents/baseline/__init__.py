"""Single-agent baseline runtime. It must not import evaluator-only truth."""

from .config import BaselineConfig
from .factory import create_baseline_agent

__all__ = ["BaselineConfig", "create_baseline_agent"]
