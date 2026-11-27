#!/usr/bin/env python3
"""Build a fixed HTML viewer and SVG beside a validated native .drawio file."""

from __future__ import annotations

import argparse
import html
import json
from pathlib import Path
import shutil
import subprocess
import xml.etree.ElementTree as ET

from check_conventions import inspect
from drawio_cli import resolve_drawio
from normalize_geometry import normalize
from preview_files import export_svg, revision, validate_svg, validate_xml
from render_svg import render, resolve_chromium, screenshot_svg

TEMPLATE = Path(__file__).resolve().parents[1] / "assets" / "viewer.html.template"


def js_value(value: object) -> str:
    return json.dumps(value, ensure_ascii=False).replace("<", "\\u003c").replace("&", "\\u0026")


def build(source: Path, output: Path, title: str, notes: dict, supplied_svg: Path | None,
          drawio_cli: str | None, review_png: bool = False, png_width: int = 2000) -> dict:
    if review_png and png_width < 1:
        raise ValueError("PNG 宽度必须为正数")
    validate_xml(source.read_bytes())
    output.mkdir(parents=True, exist_ok=True)
    target = output / source.name
    if source.resolve() != target.resolve():
        shutil.copyfile(source, target)
    tree = ET.parse(target)
    geometry_fixes, unresolved = normalize(tree)
    if unresolved:
        raise ValueError("几何修正需要人工处理：" + "; ".join(unresolved))
    if geometry_fixes:
        tree.write(target, encoding="utf-8", xml_declaration=True)
    findings = inspect(target)
    if findings:
        raise ValueError("图形规范检查失败：" + "; ".join(findings[:5]))
    xml = target.read_bytes()
    validate_xml(xml)
    svg = output / f"{source.stem}.preview.svg"
    png = output / f"{source.stem}.preview.png" if review_png else None
    executable = drawio_cli or resolve_drawio()
    if supplied_svg:
        if geometry_fixes:
            raise ValueError("泳道或端口已修正，提供的 SVG 可能过期；请重新导出 SVG")
        svg_bytes = supplied_svg.read_bytes()
        validate_svg(svg_bytes)
        if supplied_svg.resolve() != svg.resolve():
            svg.write_bytes(svg_bytes)
    elif png is not None and not executable:
        render(target, svg, png=png, png_width=png_width)
    else:
        export_svg(target, svg, executable)
    if png is not None and (supplied_svg or executable):
        if resolve_chromium():
            screenshot_svg(svg, png, png_width=png_width)
        elif executable:
            subprocess.run([executable, "-x", "-f", "png", "--width", str(png_width),
                            "-o", str(png.resolve()), str(target.resolve())],
                           capture_output=True, text=True, timeout=90, check=True)
        else:
            raise RuntimeError("缺少 Chromium，无法从现有 SVG 生成复核 PNG")
    if png is not None and (not png.is_file() or not png.stat().st_size):
        raise RuntimeError("未生成有效的复核 PNG")
    page = output / f"{source.stem}.html"
    template = TEMPLATE.read_text(encoding="utf-8")
    replacements = {
        "{{TITLE}}": html.escape(title, quote=True),
        "{{FILENAME}}": html.escape(target.name, quote=True),
        "{{SVG_FILENAME}}": html.escape(svg.name, quote=True),
        "{{XML_JSON}}": js_value(xml.decode("utf-8-sig")),
        "{{FILENAME_JSON}}": js_value(target.name),
        "{{REVISION_JSON}}": js_value(revision(xml)),
        "{{NOTES_JSON}}": js_value(notes),
    }
    for marker, value in replacements.items():
        template = template.replace(marker, value)
    page.write_text(template, encoding="utf-8")
    result = {"drawio": str(target.resolve()), "svg": str(svg.resolve()),
              "html": str(page.resolve()), "revision": revision(xml),
              "geometry_fixes": geometry_fixes}
    if png is not None:
        result["png"] = str(png.resolve())
    return result


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("drawio", type=Path)
    parser.add_argument("--output-dir", type=Path, required=True)
    parser.add_argument("--title", required=True)
    parser.add_argument("--notes-json", type=Path, help="JSON with assumptions and questions arrays")
    parser.add_argument("--svg", type=Path, help="Use a previously exported SVG")
    parser.add_argument("--drawio-cli", help="Explicit draw.io CLI path")
    parser.add_argument("--review-png", action="store_true", help="Capture a PNG from the same SVG for visual review")
    parser.add_argument("--png-width", type=int, default=2000)
    args = parser.parse_args()
    notes = json.loads(args.notes_json.read_text(encoding="utf-8")) if args.notes_json else {}
    if not isinstance(notes, dict) or any(not isinstance(notes.get(k, []), list) for k in ("assumptions", "questions")):
        parser.error("--notes-json must contain assumptions/questions arrays")
    try:
        print(json.dumps(build(args.drawio, args.output_dir, args.title, notes,
                               args.svg, args.drawio_cli, args.review_png,
                               args.png_width), ensure_ascii=False, indent=2))
    except (OSError, ValueError, RuntimeError, subprocess.SubprocessError) as exc:
        parser.exit(1, f"error: {exc}\n")


if __name__ == "__main__":
    main()
