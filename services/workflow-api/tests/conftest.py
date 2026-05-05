"""Pytest path setup for workflow-api."""

import os
import sys
from pathlib import Path

os.environ.setdefault("WORKFLOW_INIT_DB_ON_STARTUP", "false")

SERVICE_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(SERVICE_ROOT))
