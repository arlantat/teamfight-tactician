#!/usr/bin/env python3
"""Start the local Teamfight Tactician web application."""

import argparse
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "src"))

import uvicorn

from tft.config import DB_PATH, WEB_HOST, WEB_PORT
from tft.utils.logging import setup_logging
from tft.web.app import create_app


def main() -> None:
    """Parse server configuration and run the web application."""
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--host", default=WEB_HOST)
    parser.add_argument("--port", type=int, default=WEB_PORT)
    parser.add_argument("--db", type=Path, default=DB_PATH)
    args = parser.parse_args()
    setup_logging()
    uvicorn.run(create_app(args.db), host=args.host, port=args.port)


if __name__ == "__main__":
    main()
