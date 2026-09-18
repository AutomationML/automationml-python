"""Make the out-of-package evaluation harness importable in tests.

``evaluation/opcua_evaluation.py`` is development tooling and is deliberately
excluded from the distributed package, so it is not importable as
``automationml.opcua_evaluation``. Tests reach it through this path entry.
"""

import sys
from pathlib import Path

_EVALUATION = Path(__file__).resolve().parent / "evaluation"
if str(_EVALUATION) not in sys.path:
    sys.path.insert(0, str(_EVALUATION))
