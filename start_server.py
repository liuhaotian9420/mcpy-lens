#!/usr/bin/env python3
"""Startup script for mcpy-lens."""

import os
import sys

# Add src to Python path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), "src"))

from mcpy_lens.main import main

if __name__ == "__main__":
    main()
