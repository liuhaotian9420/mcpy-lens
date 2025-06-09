#!/usr/bin/env python
"""Startup script for the mcpy-lens Gradio web interface."""

import sys
from pathlib import Path

# Add the src directory to Python path
src_dir = Path(__file__).parent / "src"
sys.path.insert(0, str(src_dir))

from mcpy_lens.gradio_app.main import main

if __name__ == "__main__":
    main()
