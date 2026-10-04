#!/usr/bin/env python3
"""AutoPrevias — Radical Records. Punto de entrada principal."""

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))

from src.ui.app import launch

if __name__ == "__main__":
    target = ""
    if len(sys.argv) > 1 and Path(sys.argv[1]).is_file():
        target = sys.argv[1]
    launch(target)
