"""Main entry point for mcpy-lens application."""

import uvicorn

from mcpy_lens.app import fastapi_app
from mcpy_lens.logging_config import setup_logging

app = fastapi_app


def main() -> None:
    """Main entry point for the application."""
    setup_logging()
    uvicorn.run(
        "mcpy_lens.app:fastapi_app",
        host="0.0.0.0",
        port=8090,
        reload=True,
        log_level="info",
    )


if __name__ == "__main__":
    main()
