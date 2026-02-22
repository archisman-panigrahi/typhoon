#!/usr/bin/env python3

from __future__ import annotations

import argparse
import io
from pathlib import Path

import cairosvg
from PIL import Image


def generate_ico(svg_path: Path, ico_path: Path) -> None:
    png_bytes = cairosvg.svg2png(url=str(svg_path), output_width=512, output_height=512)
    image = Image.open(io.BytesIO(png_bytes)).convert("RGBA")
    sizes = [(16, 16), (24, 24), (32, 32), (48, 48), (64, 64), (128, 128), (256, 256)]
    ico_path.parent.mkdir(parents=True, exist_ok=True)
    image.save(ico_path, format="ICO", sizes=sizes)


def main() -> None:
    parser = argparse.ArgumentParser(description="Generate a Windows .ico file from an SVG icon.")
    parser.add_argument("svg_path", type=Path, help="Input SVG file")
    parser.add_argument("ico_path", type=Path, help="Output ICO file")
    args = parser.parse_args()
    generate_ico(args.svg_path.resolve(), args.ico_path.resolve())


if __name__ == "__main__":
    main()
