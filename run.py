#!/usr/bin/env python
"""Runner script for mcpy-lens application."""

import sys
from pathlib import Path

# Add the src directory to Python path
src_dir = Path(__file__).parent / "src"
sys.path.insert(0, str(src_dir))

from mcpy_lens.app import main

if __name__ == "__main__":
    main()
