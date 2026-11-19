#!/usr/bin/env python3
"""Export an unembedded PNG draft from a native .drawio file for visual review."""

import argparse
from pathlib import Path
import subprocess
import sys

from drawio_cli import resolve_drawio


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("input", type=Path, help="Native .drawio XML input")
    parser.add_argument("-o", "--output", type=Path, help="PNG output path")
    parser.add_argument("--width", type=int, default=2000, help="Draft width in pixels")
    parser.add_argument("--drawio-cli", type=Path, help="Explicit draw.io CLI path")
    args = parser.parse_args()

    if not args.input.is_file():
        parser.error(f"input file not found: {args.input}")
    if args.width < 1:
        parser.error("--width must be positive")
    executable = str(args.drawio_cli) if args.drawio_cli else resolve_drawio()
    if not executable:
        parser.error("draw.io desktop CLI not found; install it or pass --drawio-cli")

    output = args.output or args.input.with_suffix(".preview.png")
    output.parent.mkdir(parents=True, exist_ok=True)
    command = [executable, "-x", "-f", "png", "--width", str(args.width),
               "-o", str(output.resolve()), str(args.input.resolve())]
    try:
        subprocess.run(command, check=True)
    except (OSError, subprocess.CalledProcessError) as exc:
        print(f"draw.io export failed: {exc}", file=sys.stderr)
        return 1
    if not output.is_file() or output.stat().st_size == 0:
        print(f"draw.io did not create a nonempty PNG: {output}", file=sys.stderr)
        return 1
    print(output.resolve())
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
