"""Serve generated full-pitch reports over localhost."""

from __future__ import annotations

import argparse
from functools import partial
from http.server import SimpleHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path


def safe_print(message: str) -> None:
    try:
        print(message)
    except OSError:
        pass


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description="Serve videos/output/full_pitch_test so Chrome can open video links safely."
    )
    parser.add_argument(
        "--directory",
        type=Path,
        default=Path("videos/output/full_pitch_test"),
        help="Directory to serve. Defaults to videos/output/full_pitch_test.",
    )
    parser.add_argument("--host", default="127.0.0.1", help="Host to bind.")
    parser.add_argument("--port", type=int, default=8765, help="Port to bind.")
    return parser


def main() -> None:
    args = build_parser().parse_args()
    directory = args.directory.resolve()
    if not directory.exists():
        raise FileNotFoundError(directory)

    handler = partial(SimpleHTTPRequestHandler, directory=str(directory))
    server = ThreadingHTTPServer((args.host, args.port), handler)
    url = f"http://{args.host}:{args.port}/index.html"
    safe_print(f"Serving {directory}")
    safe_print(f"Open {url}")
    server.serve_forever()


if __name__ == "__main__":
    main()
