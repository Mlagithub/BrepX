"""CLI runner for independent BrepX Agent process."""

from __future__ import annotations

import argparse
import sys
import uvicorn


def main() -> None:
    parser = argparse.ArgumentParser(description="BrepX Isolated Agent Process Service")
    parser.add_argument("--host", default="127.0.0.1", help="Host interface to bind")
    parser.add_argument("--port", type=int, default=8081, help="Port to listen on (default: 8081)")
    args = parser.parse_args()

    print(f"Starting isolated BrepX Agent process on http://{args.host}:{args.port}")
    uvicorn.run("backend.adapters.agent.main:app", host=args.host, port=args.port, reload=False)


if __name__ == "__main__":
    main()
