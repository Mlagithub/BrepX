"""python -m cadwork.service --port 8765"""

from __future__ import annotations

import argparse
import os

import uvicorn

from .app import create_app


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Serve the cadwork HTTP + MCP surface.")
    parser.add_argument("--host", default="127.0.0.1")
    parser.add_argument("--port", type=int, default=8765)
    parser.add_argument("--home", default=os.environ.get("CADWORK_HOME"),
                        help="document store directory (default: ./cadwork-data)")
    args = parser.parse_args(argv)
    uvicorn.run(create_app(args.home), host=args.host, port=args.port, log_level="info")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
