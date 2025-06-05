"""Main entry point for mcpy-lens application."""

import sys
from pathlib import Path

# Add the src directory to Python path
src_dir = Path(__file__).parent.parent
if str(src_dir) not in sys.path:
    sys.path.insert(0, str(src_dir))

from mcpy_lens.app import main

if __name__ == "__main__":
    main()
